from typing import Optional
from pathlib import Path as FilePath
import re
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from app.schemas import (
    DownloadJob,
    DownloadJobStatus,
    BookSearchQuery,
    DownloadLibraryResponse,
    DownloadLibraryItem
)
from app.db.repository import repository
from app.services.safe_downloader import safe_downloader
from app.services.web_search import load_mock_candidates

router = APIRouter(tags=["Safe Download Pipeline"])


class DownloadTriggerRequest(BaseModel):
    approval_id: Optional[str] = Field(
        default=None,
        description="Optional approval ID. If omitted, uses active approval for this candidate."
    )
    simulate_only: bool = Field(
        default=False,
        description="Dry-run simulation mode to test validation gates without downloading real files."
    )


@router.get("/candidates/{candidate_id}/download-file")
async def stream_candidate_download(
    candidate_id: str = Path(..., description="ID of the candidate to download"),
    format: Optional[str] = Query("PDF", description="Requested format: PDF or EPUB")
):
    """
    Direct, authorized file download endpoint:
    - Verifies candidate exists and is legally downloadable.
    - Executes safe download pipeline (validation, quarantine, hash check).
    - Returns FileResponse streaming the validated PDF/EPUB to client.
    """
    candidate = repository.get_candidate(candidate_id)
    if not candidate:
        mocks = load_mock_candidates(BookSearchQuery())
        for m in mocks:
            if m.candidate_id == candidate_id:
                candidate = m
                break

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found.")

    if not candidate.licensing or not candidate.licensing.is_legally_downloadable:
        raise HTTPException(
            status_code=403,
            detail="In-copyright work. Direct file downloading is strictly prohibited by policy."
        )

    req_format = (format or "PDF").upper()
    target_url = (candidate.epub_url if req_format == "EPUB" else (candidate.pdf_url or candidate.download_url))
    if not target_url:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate '{candidate.title}' has no authorized direct {req_format} download URL."
        )

    job = await safe_downloader.execute_download(
        candidate=candidate,
        format=req_format,
        simulate_only=False
    )

    if job.status in (DownloadJobStatus.COMPLETED, DownloadJobStatus.DUPLICATE):
        clean_title = re.sub(r"[^a-zA-Z0-9_\-\s]", "", candidate.title or "book").strip()
        clean_title = re.sub(r"\s+", "_", clean_title) or "book"
        ext = "epub" if req_format == "EPUB" else "pdf"
        media_type = "application/epub+zip" if req_format == "EPUB" else "application/pdf"

        if job.file_path and FilePath(job.file_path).exists():
            return FileResponse(
                path=job.file_path,
                media_type=media_type,
                filename=f"{clean_title}.{ext}"
            )
        else:
            return RedirectResponse(url=target_url)
    else:
        err_msg = job.error_message or ""
        is_restricted = any(kw in err_msg.lower() for kw in ["403", "429", "forbidden", "rate limit", "paywall", "markup", "content type", "html"])
        fallback_url = candidate.reader_url or candidate.embed_url or candidate.preview_url or candidate.source_url
        if is_restricted and fallback_url:
            logger.info(f"Direct download hit repository restriction ({err_msg}). Gracefully redirecting to Reading Workspace preview URL: {fallback_url}")
            return RedirectResponse(url=fallback_url, status_code=307)

        raise HTTPException(
            status_code=502,
            detail=f"Download failed: {job.error_message or 'Unable to acquire verified copy from repository.'}"
        )


@router.post("/candidates/{candidate_id}/download", response_model=DownloadJob)
async def request_candidate_download(
    candidate_id: str = Path(..., description="ID of the approved candidate to acquire"),
    request: Optional[DownloadTriggerRequest] = None
):
    """
    Download only after explicit approval and successful server-side eligibility checks.
    Pipeline:
      1. Revalidates prior explicit user approval & expiration.
      2. Re-verifies legal licensing status (VERIFIED_FOR_PERMITTED_DOWNLOAD).
      3. Performs SSRF and repository domain validation on download URL.
      4. Downloads stream with max file size limit.
      5. Validates file header and readability via pypdf.
      6. Detects duplicates via SHA-256 database lookup.
      7. Quarantines invalid files and records provenance for valid acquisitions.
    """
    candidate = repository.get_candidate(candidate_id)
    if not candidate:
        mocks = load_mock_candidates(BookSearchQuery())
        for m in mocks:
            if m.candidate_id == candidate_id:
                candidate = m
                break

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate '{candidate_id}' not found."
        )

    appr_id = request.approval_id if request else None
    sim_only = request.simulate_only if request else False

    job = await safe_downloader.execute_download(
        candidate=candidate,
        approval_id=appr_id,
        simulate_only=sim_only
    )
    return job


@router.get("/downloads/library", response_model=DownloadLibraryResponse)
async def list_download_library():
    """
    Retrieve all verified acquired books stored in the centralized download library.
    """
    items = repository.get_download_library_items()
    return DownloadLibraryResponse(
        total_items=len(items),
        items=items
    )


@router.get("/downloads/library/{job_id}/stream")
async def stream_library_item(
    job_id: str = Path(..., description="Job ID of the downloaded book"),
    download: bool = Query(False, description="Whether to trigger file download attachment")
):
    """
    Stream or download an acquired book from the local library.
    """
    items = repository.get_download_library_items()
    item = next((it for it in items if it.job_id == job_id), None)
    if not item:
        raise HTTPException(status_code=404, detail=f"Download library item '{job_id}' not found.")

    p = FilePath(item.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Physical book file is missing or has been moved.")

    media_type = "application/epub+zip" if item.format == "EPUB" else "application/pdf"
    content_disposition = "attachment" if download else "inline"

    clean_filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', item.title)}.{item.format.lower()}"

    return FileResponse(
        path=str(p),
        media_type=media_type,
        filename=clean_filename,
        content_disposition_type=content_disposition
    )


@router.delete("/downloads/library/{job_id}")
async def delete_library_item(
    job_id: str = Path(..., description="Job ID of the downloaded book to remove")
):
    """
    Delete an acquired book file from disk and remove its record from the library.
    """
    success = repository.delete_download_library_item(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Failed to delete download library item '{job_id}'.")
    return {"message": f"Successfully removed '{job_id}' from the library."}
