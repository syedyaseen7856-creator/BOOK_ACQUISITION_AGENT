import logging
import uuid
import shutil
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException
from app.config import settings
from app.db.repository import repository
from app.schemas import (
    BookCandidate,
    ApprovalRecord,
    DownloadJob,
    DownloadJobStatus,
    LicenseStatus
)
from app.services.approval_service import approval_service
from app.services.download_safety import validate_download_url, sanitize_filename
from app.services.file_validator import validate_pdf_file, validate_epub_file, quarantine_file
from app.services.duplicate_detector import check_for_duplicate

logger = logging.getLogger(__name__)


class SafeDownloader:
    """
    Executes secure book acquisitions with end-to-end safeguards:
      - Mandatory approval revalidation & expiry check
      - Legal licensing re-verification
      - SSRF & domain protection
      - Streamed download with size limit enforcement
      - PDF validation via pypdf / EPUB structural validation
      - SHA-256 duplicate detection
      - Quarantine isolation for invalid files
    """

    async def execute_download(
        self,
        candidate: BookCandidate,
        approval_id: Optional[str] = None,
        simulate_only: bool = False,
        format: Optional[str] = None,
        syllabus_name: Optional[str] = None,
        semester: Optional[str] = None,
        subject_name: Optional[str] = None
    ) -> DownloadJob:
        """
        Execute the download pipeline for an approved candidate.
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 0: Resolve format (PDF vs EPUB)
        req_format = (format or "").upper()
        if not req_format:
            if candidate.epub_url and not candidate.pdf_url:
                req_format = "EPUB"
            elif candidate.format and candidate.format.upper() == "EPUB" and not candidate.pdf_url:
                req_format = "EPUB"
            else:
                req_format = "PDF"

        if req_format == "EPUB":
            target_url = candidate.epub_url or candidate.download_url
        else:
            target_url = candidate.pdf_url or candidate.download_url

        if not target_url:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate '{candidate.title}' has no direct download URL available for format '{req_format}'."
            )

        # Step 1: Revalidate server-side approval and licensing
        if not approval_id:
            # Check for active non-expired approval in database
            active_appr = repository.get_active_approval_for_candidate(candidate.candidate_id)
            if active_appr and not active_appr.is_expired:
                approval_id = active_appr.approval_id

        # If no prior approval exists but candidate is verified for permitted download,
        # record an automatic user-affirmed approval
        if not approval_id:
            if candidate.licensing.status == LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD and candidate.licensing.is_legally_downloadable:
                from app.schemas import CandidateApprovalRequest
                new_appr = approval_service.approve_candidate(
                    candidate=candidate,
                    request=CandidateApprovalRequest(
                        user_affirmation=True,
                        user_note=f"Authorized download of verified public domain / open access {req_format} copy."
                    )
                )
                approval_id = new_appr.approval_id

        is_approved, approval_msg, approval_record = approval_service.validate_approval_for_download(
            candidate=candidate,
            approval_id=approval_id
        )

        if not is_approved or not approval_record:
            raise HTTPException(status_code=403, detail=f"Download authorization rejected: {approval_msg}")

        # Step 2: Validate download URL safety
        is_safe_url, safety_msg = validate_download_url(target_url)
        if not is_safe_url:
            raise HTTPException(
                status_code=400,
                detail=f"Security safeguard triggered on download URL: {safety_msg}"
            )

        # Initialize DownloadJob in SQLite
        job = DownloadJob(
            job_id=job_id,
            candidate_id=candidate.candidate_id,
            approval_id=approval_record.approval_id,
            status=DownloadJobStatus.PENDING,
            progress=0,
            created_at=now_iso
        )
        repository.create_download_job(job)

        # Milestone 1 / Simulation Safeguard
        if simulate_only or settings.APP_ENV == "testing":
            job.status = DownloadJobStatus.COMPLETED
            job.progress = 100
            job.error_message = None
            job.file_path = str(settings.downloads_path / f"test_simulated_{candidate.candidate_id}.{'epub' if req_format == 'EPUB' else 'pdf'}")
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.provenance = {
                "simulation": True,
                "note": f"Milestone gate tested: approval, licensing, and URL safety validated for {req_format} with zero file download."
            }
            repository.update_download_job(job)
            return job

        # Step 3: Streamed download with size limits
        ext = ".epub" if req_format == "EPUB" else ".pdf"
        raw_name = Path(target_url.split("?")[0]).name or f"book{ext}"
        if not raw_name.lower().endswith(ext):
            raw_name += ext

        safe_name = sanitize_filename(f"{candidate.candidate_id}_{raw_name}")
        temp_path = settings.downloads_path / f"tmp_{job_id}_{safe_name}"
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        job.status = DownloadJobStatus.DOWNLOADING
        job.progress = 20
        repository.update_download_job(job)

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                async with client.stream("GET", target_url) as resp:
                    # Validate redirect chain for SSRF protection
                    for redirect_resp in resp.history:
                        is_safe_redir, redir_msg = validate_download_url(str(redirect_resp.url))
                        if not is_safe_redir:
                            job.status = DownloadJobStatus.FAILED
                            job.error_message = f"Redirect chain blocked: {redir_msg}"
                            job.completed_at = datetime.now(timezone.utc).isoformat()
                            repository.update_download_job(job)
                            return job

                    final_safe, final_msg = validate_download_url(str(resp.url))
                    if not final_safe:
                        job.status = DownloadJobStatus.FAILED
                        job.error_message = f"Final destination URL blocked: {final_msg}"
                        job.completed_at = datetime.now(timezone.utc).isoformat()
                        repository.update_download_job(job)
                        return job

                    if resp.status_code != 200:
                        fallback_url = candidate.reader_url or candidate.embed_url or candidate.preview_url or candidate.source_url
                        job.status = DownloadJobStatus.FAILED
                        job.error_message = f"Repository returned HTTP {resp.status_code}: resource access restricted or rate limited."
                        job.provenance = {
                            "status_code": resp.status_code,
                            "fallback_preview_url": fallback_url
                        }
                        job.completed_at = datetime.now(timezone.utc).isoformat()
                        repository.update_download_job(job)
                        return job

                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "text/html" in content_type:
                        job.status = DownloadJobStatus.FAILED
                        job.error_message = f"Invalid content type '{content_type}': expected digital book binary, received HTML."
                        job.completed_at = datetime.now(timezone.utc).isoformat()
                        repository.update_download_job(job)
                        return job

                    total_downloaded = 0
                    first_chunk = True
                    with open(temp_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            if first_chunk:
                                # Check for HTML error pages served with generic binary mime types
                                chunk_start = chunk[:256].lower()
                                if b"<!doctype html" in chunk_start or b"<html" in chunk_start:
                                    temp_path.unlink(missing_ok=True)
                                    job.status = DownloadJobStatus.FAILED
                                    job.error_message = "Stream begins with HTML markup instead of book binary (e.g. paywall/error page). HTML pages are never saved as book files."
                                    job.completed_at = datetime.now(timezone.utc).isoformat()
                                    repository.update_download_job(job)
                                    return job
                                first_chunk = False

                            total_downloaded += len(chunk)
                            if total_downloaded > max_bytes:
                                temp_path.unlink(missing_ok=True)
                                job.status = DownloadJobStatus.FAILED
                                job.error_message = f"File exceeded maximum permitted size ({settings.MAX_FILE_SIZE_MB}MB)."
                                job.completed_at = datetime.now(timezone.utc).isoformat()
                                repository.update_download_job(job)
                                return job
                            f.write(chunk)

            # Step 4: Validate File Structure (pypdf for PDF, zip validator for EPUB)
            job.status = DownloadJobStatus.VALIDATING
            job.progress = 60
            repository.update_download_job(job)

            if req_format == "EPUB":
                is_valid, val_msg, val_meta = validate_epub_file(temp_path)
            else:
                is_valid, val_msg, val_meta = validate_pdf_file(temp_path)

            if not is_valid:
                # Quarantine suspicious or corrupted file
                q_path = quarantine_file(temp_path, reason=val_msg)
                job.status = DownloadJobStatus.QUARANTINED
                job.file_path = str(q_path)
                job.error_message = f"File validation failed and was quarantined: {val_msg}"
                job.completed_at = datetime.now(timezone.utc).isoformat()
                repository.update_download_job(job)
                return job

            file_hash = val_meta["file_hash"]
            file_size = val_meta["file_size_bytes"]
            page_count = val_meta.get("page_count")

            # Step 5: Duplicate Detection via SHA-256
            is_dup, dup_record = check_for_duplicate(file_hash)
            if is_dup and dup_record:
                temp_path.unlink(missing_ok=True)
                job.status = DownloadJobStatus.DUPLICATE
                job.file_path = dup_record.get("file_path")
                job.file_hash = file_hash
                job.file_size_bytes = file_size
                job.page_count = page_count
                job.error_message = f"Duplicate file detected: already acquired as candidate '{dup_record.get('candidate_id')}'."
                job.provenance = dup_record
                job.completed_at = datetime.now(timezone.utc).isoformat()
                repository.update_download_job(job)
                return job

            # Step 6: Move to permanent storage & record provenance
            # Syllabus acquisitions: downloads/{Syllabus_Name}/{Semester}/{Subject_Name}/{Book_Title}.pdf
            # Individual searches: downloads/Individual_Books/{Book_Title_Author}.pdf
            ext = ".epub" if req_format == "EPUB" else ".pdf"
            if syllabus_name:
                clean_syl = sanitize_filename(re.sub(r"[^\w\s-]", "", syllabus_name).strip() or "Syllabus")
                clean_sem = sanitize_filename(re.sub(r"[^\w\s-]", "", semester or "General").strip() or "General")
                clean_subj = sanitize_filename(re.sub(r"[^\w\s-]", "", subject_name or "General").strip() or "General")
                target_dir = settings.downloads_path / clean_syl / clean_sem / clean_subj
                clean_b_title = sanitize_filename(re.sub(r"[^\w\s-]", "", candidate.title).strip() or "book")
                book_file_name = f"{clean_b_title}{ext}"
            else:
                target_dir = settings.downloads_path / "Individual_Books"
                clean_b_title = sanitize_filename(re.sub(r"[^\w\s-]", "", candidate.title).strip() or "book")
                author_str = f" - {sanitize_filename(re.sub(r'[^\w\s-]', '', candidate.authors[0]))}" if candidate.authors else ""
                book_file_name = f"{clean_b_title}{author_str}{ext}"

            target_dir.mkdir(parents=True, exist_ok=True)
            final_path = target_dir / book_file_name

            if final_path.exists() and final_path != temp_path:
                final_path = target_dir / f"{job_id}_{book_file_name}"

            shutil.move(str(temp_path), str(final_path))

            provenance_data = {
                "job_id": job_id,
                "candidate_id": candidate.candidate_id,
                "title": candidate.title,
                "authors": candidate.authors,
                "publisher": candidate.publisher,
                "published_year": candidate.published_year,
                "edition": candidate.edition,
                "isbns": candidate.isbns,
                "page_count": page_count,
                "file_hash": file_hash,
                "file_path": str(final_path),
                "file_size_bytes": file_size,
                "source_name": candidate.source_name,
                "source_url": candidate.source_url,
                "license_status": candidate.licensing.status.value,
                "license_name": candidate.licensing.license_name,
                "approval_id": approval_record.approval_id,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "intended_use": candidate.licensing.intended_use,
                "syllabus_name": syllabus_name,
                "semester": semester,
                "subject_name": subject_name,
                "format": req_format
            }

            repository.save_provenance(
                file_hash=file_hash,
                candidate_id=candidate.candidate_id,
                job_id=job_id,
                file_path=str(final_path),
                provenance=provenance_data
            )

            job.status = DownloadJobStatus.COMPLETED
            job.progress = 100
            job.file_path = str(final_path)
            job.file_hash = file_hash
            job.file_size_bytes = file_size
            job.page_count = page_count
            job.provenance = provenance_data
            job.completed_at = datetime.now(timezone.utc).isoformat()
            repository.update_download_job(job)

            logger.info(f"Successfully downloaded and verified candidate {candidate.candidate_id} to {final_path}")
            return job

        except Exception as e:
            logger.error(f"Download pipeline exception for job {job_id}: {e}", exc_info=True)
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            job.status = DownloadJobStatus.FAILED
            job.error_message = f"Download pipeline exception: {str(e)}"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            repository.update_download_job(job)
            return job


safe_downloader = SafeDownloader()
