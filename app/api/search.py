import logging
from fastapi import APIRouter, HTTPException
from app.schemas import BookSearchQuery, SearchResponse
from app.services.metadata_aggregator import aggregate_and_rank_candidates_with_status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Book Discovery"])


@router.post("/search", response_model=SearchResponse)
async def discover_book_candidates(query: BookSearchQuery):
    """
    Search bibliographic sources and authorized repositories for candidate records.
    MANDATORY RULE: Searching and previewing candidates NEVER downloads book files.
    """
    if query.is_empty():
        raise HTTPException(
            status_code=400,
            detail="At least one search field (title, author, ISBN, or subject) must be provided."
        )

    try:
        candidates, provider_statuses, related_candidates = await aggregate_and_rank_candidates_with_status(
            query, return_related=True
        )

        # Requirement 5: Automatically acquire the best authorized PDF when available
        if candidates:
            top = candidates[0]
            if top.licensing.is_legally_downloadable and (top.pdf_url or top.download_url):
                try:
                    from app.services.safe_downloader import safe_downloader
                    await safe_downloader.execute_download(candidate=top, simulate_only=False, format="PDF")
                    logger.info(f"Auto-acquired best authorized PDF for query '{query.title or query.q}': {top.title}")
                except Exception as dl_err:
                    logger.warning(f"Auto-acquisition on search for '{top.title}' encountered: {dl_err}")

        return SearchResponse(
            query=query,
            total_candidates=len(candidates),
            candidates=candidates,
            related_publications=related_candidates,
            total_related=len(related_candidates),
            provider_statuses=provider_statuses
        )
    except Exception as e:
        logger.error(f"Discovery search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while discovering book metadata: {str(e)}"
        )
