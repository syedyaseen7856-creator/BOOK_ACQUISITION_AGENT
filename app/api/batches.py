import uuid
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    BatchSearchStatusResponse,
    BatchBookItem,
    SearchBatchCreateRequest
)
from app.db.repository import repository
from app.services.batch_orchestrator import batch_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Multi-Book Parallel Search"])


@router.post("/syllabus/{syllabus_id}/search-batch", response_model=BatchSearchStatusResponse)
async def create_syllabus_search_batch(
    syllabus_id: str,
    request: Optional[SearchBatchCreateRequest] = None
):
    """
    Launch a bounded concurrent search for all selected reference books
    extracted from the syllabus.
    """
    syl = repository.get_syllabus_upload(syllabus_id)
    if not syl:
        raise HTTPException(status_code=404, detail="Syllabus not found.")

    all_books = repository.get_extracted_books(syllabus_id)
    if not all_books:
        raise HTTPException(status_code=400, detail="No extracted books found for this syllabus.")

    # Filter to selected books
    if request and request.book_ids:
        selected_books = [b for b in all_books if b.id in request.book_ids]
    else:
        selected_books = [b for b in all_books if b.is_selected]

    if not selected_books:
        raise HTTPException(status_code=400, detail="No books are selected for acquisition search.")

    batch_id = f"batch_{uuid.uuid4().hex[:10]}"
    now_iso = syl["created_at"]

    batch_items: list[BatchBookItem] = []
    for b in selected_books:
        batch_items.append(
            BatchBookItem(
                id=f"item_{uuid.uuid4().hex[:10]}",
                batch_id=batch_id,
                extracted_book_id=b.id,
                title=b.title,
                author=b.author,
                isbn=b.isbn,
                subject=b.subject,
                status="PENDING",
                results_count=0,
                top_candidate=None,
                access_classification="UNVERIFIED",
                provider_statuses=[],
                error_message=None,
                updated_at=now_iso
            )
        )

    batch_orchestrator.start_batch(batch_id, syllabus_id, batch_items)

    status_resp = batch_orchestrator.get_batch_status(batch_id)
    if not status_resp:
        raise HTTPException(status_code=500, detail="Failed to initialize batch search.")
    return status_resp


@router.get("/batches/{batch_id}", response_model=BatchSearchStatusResponse)
async def get_batch_status(
    batch_id: str,
    filter: Optional[str] = Query(default=None, description="Filter: ALL, FREE_FULL_TEXT, DOWNLOADABLE, PREVIEW, BORROW, NOT_ELIGIBLE, NO_RESULTS, FAILED, IN_PROGRESS")
):
    """
    Retrieve real-time status of a search batch, including per-book progress,
    provider statuses, access classifications, and candidate metadata.
    """
    status_resp = batch_orchestrator.get_batch_status(batch_id, access_filter=filter)
    if not status_resp:
        raise HTTPException(status_code=404, detail=f"Search batch '{batch_id}' not found.")
    return status_resp


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """
    Cancel an ongoing multi-book search batch.
    """
    batch = repository.get_search_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Search batch not found.")

    batch_orchestrator.cancel_batch(batch_id)
    return {"message": f"Search batch '{batch_id}' cancelled.", "batch_id": batch_id}


@router.post("/batches/{batch_id}/retry", response_model=BatchSearchStatusResponse)
async def retry_batch(batch_id: str):
    """
    Retry failed or no-result books in a search batch.
    """
    batch = repository.get_search_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Search batch not found.")

    batch_orchestrator.retry_batch(batch_id)
    status_resp = batch_orchestrator.get_batch_status(batch_id)
    return status_resp
