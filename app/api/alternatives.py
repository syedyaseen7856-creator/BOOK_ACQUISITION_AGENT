import logging
from fastapi import APIRouter, HTTPException

from app.schemas import AlternativeBookResponse
from app.db.repository import repository
from app.services.alternative_finder import alternative_finder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Open-Access Alternative Finder"])


@router.get("/candidates/{candidate_id}/alternative", response_model=AlternativeBookResponse)
async def find_open_alternatives_for_candidate(candidate_id: str):
    """
    Search for legitimate open-access alternatives (OpenStax textbooks,
    Gutenberg public domain editions, or library borrowing) when a book
    is commercial, restricted, or unavailable for authorized download.
    """
    candidate = repository.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate record not found.")

    try:
        response = await alternative_finder.find_alternatives(candidate)
        return response
    except Exception as e:
        logger.error(f"Error finding alternatives for candidate '{candidate_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find alternatives: {str(e)}"
        )
