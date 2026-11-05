from typing import List
from fastapi import APIRouter, HTTPException, Path
from app.schemas import (
    ApprovalRecord,
    CandidateApprovalRequest,
    BookSearchQuery
)
from app.db.repository import repository
from app.services.approval_service import approval_service
from app.services.web_search import load_mock_candidates

router = APIRouter(tags=["Candidate Approval"])


@router.post("/candidates/{candidate_id}/approve", response_model=ApprovalRecord)
async def approve_candidate(
    candidate_id: str = Path(..., description="ID of the candidate to approve"),
    request: CandidateApprovalRequest = ...
):
    """
    Explicitly approve a verified book candidate for acquisition after server-side eligibility checks.
    Enforces server-side safeguards:
      - Requires explicit user affirmation.
      - Blocks approval for commercial/in-copyright or unverified candidates (403 Forbidden).
      - Generates snapshot hash and assigns expiration window.
    """
    candidate = repository.get_candidate(candidate_id)
    if not candidate:
        # Fallback to mock catalog for testing
        mocks = load_mock_candidates(BookSearchQuery())
        for m in mocks:
            if m.candidate_id == candidate_id:
                candidate = m
                break

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate '{candidate_id}' not found. Cannot approve an unregistered candidate."
        )

    record = approval_service.approve_candidate(candidate, request)
    return record


@router.get("/approvals", response_model=List[ApprovalRecord])
async def list_approvals():
    """Retrieve audit history of all recorded candidate approvals."""
    return approval_service.list_approvals()


@router.get("/approvals/{approval_id}", response_model=ApprovalRecord)
async def get_approval(
    approval_id: str = Path(..., description="The unique approval record identifier")
):
    """Retrieve an individual approval record with expiration and snapshot hash details."""
    record = approval_service.get_approval(approval_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Approval record '{approval_id}' was not found."
        )
    return record
