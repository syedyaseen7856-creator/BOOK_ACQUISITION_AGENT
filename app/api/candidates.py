from fastapi import APIRouter, HTTPException, Path
from app.schemas import BookCandidate, BookSearchQuery
from app.db.repository import repository
from app.services.web_search import load_mock_candidates

router = APIRouter(tags=["Candidate Inspection"])


@router.get("/candidates/{candidate_id}", response_model=BookCandidate)
async def get_candidate_details(
    candidate_id: str = Path(..., description="Unique ID of the discovered book candidate")
):
    """
    Return candidate metadata, explainable confidence breakdown, and licensing evidence.
    """
    candidate = repository.get_candidate(candidate_id)
    if candidate:
        return candidate

    # Fallback to mock catalog lookup if not yet persisted from an active search
    mocks = load_mock_candidates(BookSearchQuery())
    for m in mocks:
        if m.candidate_id == candidate_id:
            return m

    raise HTTPException(
        status_code=404,
        detail=f"Candidate with ID '{candidate_id}' was not found in the repository."
    )
