import logging
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.book import BookSearchQuery, BookCandidate
from app.services.metadata_aggregator import aggregate_and_rank_candidates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Search & Metadata Discovery"])


class SearchResponse(BaseModel):
    query: BookSearchQuery
    total_candidates: int
    candidates: List[BookCandidate]


@router.post("/search", response_model=SearchResponse)
async def search_books(query: BookSearchQuery):
    """
    Search metadata sources and authorized book repositories,
    calculate explainable confidence scores, verify licensing independently,
    and return ranked candidates.
    """
    if query.is_empty():
        raise HTTPException(
            status_code=400,
            detail="At least one search field (title, author, or ISBN) must be provided."
        )

    try:
        candidates = await aggregate_and_rank_candidates(query)
        return SearchResponse(
            query=query,
            total_candidates=len(candidates),
            candidates=candidates
        )
    except Exception as e:
        logger.error(f"Search endpoint failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while discovering book metadata: {str(e)}"
        )
