import logging
from typing import List
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from app.models.audit import (
    CandidateApprovalRequest,
    ApprovalRecord
)
from app.services.approval_service import approval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Candidate Approval"])


class ApprovalResponse(BaseModel):
    status: str
    message: str
    record: ApprovalRecord


@router.post("/approval", response_model=ApprovalResponse)
async def submit_candidate_approval(request: CandidateApprovalRequest):
    """
    Explicitly approve a verified book candidate for acquisition.
    Enforces per-book approval and validates legal licensing.
    """
    record = approval_service.approve_candidate(request)
    return ApprovalResponse(
        status="approved",
        message=f"Candidate '{record.book_title}' successfully approved for acquisition.",
        record=record
    )


@router.get("/approvals", response_model=List[ApprovalRecord])
async def list_all_approvals():
    """Retrieve audit history of all approved candidates."""
    return approval_service.list_approvals()


@router.get("/approvals/{approval_id}", response_model=ApprovalRecord)
async def get_single_approval(
    approval_id: str = Path(..., description="The unique approval record identifier")
):
    """Retrieve a specific candidate approval audit record."""
    record = approval_service.get_approval(approval_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Approval record '{approval_id}' not found."
        )
    return record
