import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.approval_service import approval_service
from app.services.download_safety import validate_download_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Download Pipeline (Milestone 2 Foundation)"])


class DownloadExecutionRequest(BaseModel):
    approval_id: str = Field(..., description="Audit ID of the approved candidate record.")
    override_reason: Optional[str] = Field(default=None, description="Optional override reason.")


class DownloadExecutionResponse(BaseModel):
    status: str
    download_allowed: bool
    milestone_note: str
    approval_id: str
    book_title: str
    target_url: Optional[str]
    url_safety_check: str
    file_integrity_hash: Optional[str] = None


@router.post("/download", response_model=DownloadExecutionResponse)
async def request_book_download(request: DownloadExecutionRequest):
    """
    Download execution endpoint.
    Safeguards:
    1. Revalidates prior explicit user approval.
    2. Revalidates legal licensing status.
    3. Performs SSRF, scheme, and domain safety verification on target URL.
    4. Milestone 1 enforces dry-run/preview safeguard: No real files downloaded.
    """
    record = approval_service.get_approval(request.approval_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No valid approval found for ID '{request.approval_id}'. Downloads require explicit prior approval."
        )

    if not record.is_legally_downloadable:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Download blocked by mandatory safeguard: Candidate '{record.book_title}' is marked "
                f"'{record.licensing_status}' and is not authorized for file acquisition."
            )
        )

    if not record.download_url:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate '{record.book_title}' does not have a downloadable file URL available."
        )

    # Perform URL and SSRF validation
    is_safe, safety_msg = validate_download_url(record.download_url)
    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail=f"Security safeguard triggered: {safety_msg}"
        )

    # In Milestone 1, real downloads are strictly disabled per specifications:
    # "Build only the search, candidate ranking, license-status display, and approval interface first. Do not download real books yet."
    return DownloadExecutionResponse(
        status="milestone_1_safe_stub",
        download_allowed=True,
        milestone_note="First development milestone active: search, ranking, licensing, and approvals verified. Real downloads are disabled in Milestone 1.",
        approval_id=record.approval_id,
        book_title=record.book_title,
        target_url=record.download_url,
        url_safety_check=safety_msg,
        file_integrity_hash=None
    )
