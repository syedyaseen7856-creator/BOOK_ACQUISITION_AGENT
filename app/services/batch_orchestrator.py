import asyncio
import logging
import uuid
from typing import Dict, Optional, List, Set
from datetime import datetime, timezone

from app.schemas import (
    BatchBookItem,
    BookSearchQuery,
    BookCandidate,
    LicenseStatus,
    DownloadJobStatus,
    BatchSearchStatusResponse
)
from app.db.repository import repository
from app.services.metadata_aggregator import aggregate_and_rank_candidates_with_status
from app.services.safe_downloader import safe_downloader

logger = logging.getLogger(__name__)

# Concurrency limit to prevent hitting API quotas or rate limits
DEFAULT_CONCURRENCY = 3


class BatchOrchestrator:
    """
    Manages bounded asynchronous parallel multi-book searches with:
      - Per-book progress tracking & provider statuses
      - Concurrency limits (Semaphore)
      - Graceful cancellation & retry handling
      - Access classification
      - SQLite state persistence
    """

    def __init__(self):
        self._cancelled_batches: Set[str] = set()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)

    def start_batch(self, batch_id: str, syllabus_id: Optional[str], books: List[BatchBookItem]) -> str:
        """
        Create batch in SQLite, insert book items, and launch background worker.
        """
        repository.create_search_batch(
            batch_id=batch_id,
            syllabus_id=syllabus_id,
            total_books=len(books)
        )

        for b in books:
            repository.add_batch_book_item(b)

        # Launch async worker
        task = asyncio.create_task(self._process_batch(batch_id, books))
        self._running_tasks[batch_id] = task
        return batch_id

    def cancel_batch(self, batch_id: str) -> bool:
        """Flag batch for cancellation and update database status."""
        self._cancelled_batches.add(batch_id)
        if batch_id in self._running_tasks:
            self._running_tasks[batch_id].cancel()
        repository.update_search_batch_status(batch_id, status="CANCELLED")
        logger.info(f"Batch '{batch_id}' marked as CANCELLED.")
        return True

    def retry_batch(self, batch_id: str) -> Optional[str]:
        """
        Retry failed or incomplete books in an existing batch.
        """
        batch = repository.get_search_batch(batch_id)
        if not batch:
            return None

        items = repository.get_batch_book_items(batch_id)
        to_retry = [it for it in items if it.status in ("FAILED", "NO_RESULTS", "PENDING")]

        if not to_retry:
            logger.info(f"No retryable items in batch '{batch_id}'.")
            return batch_id

        # Reset items
        for it in to_retry:
            it.status = "PENDING"
            it.error_message = None
            repository.update_batch_book_item(it)

        self._cancelled_batches.discard(batch_id)
        repository.update_search_batch_status(
            batch_id=batch_id,
            status="RUNNING",
            completed_books=len(items) - len(to_retry),
            failed_books=0
        )

        task = asyncio.create_task(self._process_batch(batch_id, to_retry, resume=True))
        self._running_tasks[batch_id] = task
        return batch_id

    async def _process_batch(self, batch_id: str, items: List[BatchBookItem], resume: bool = False):
        """Worker executing searches with bounded concurrency."""
        repository.update_search_batch_status(batch_id, status="RUNNING")
        logger.info(f"Started processing batch '{batch_id}' with {len(items)} book(s).")

        batch_record = repository.get_search_batch(batch_id)
        syl_record = repository.get_syllabus_upload(batch_record["syllabus_id"]) if (batch_record and batch_record.get("syllabus_id")) else None
        syl_filename = syl_record["filename"].rsplit(".", 1)[0] if syl_record else None
        syl_semester = syl_record.get("semester") if syl_record else None

        async def _search_single_book(item: BatchBookItem):
            if batch_id in self._cancelled_batches:
                item.status = "CANCELLED"
                repository.update_batch_book_item(item)
                return

            async with self._semaphore:
                if batch_id in self._cancelled_batches:
                    return

                item.status = "SEARCHING"
                repository.update_batch_book_item(item)

                query = BookSearchQuery(
                    title=item.title,
                    author=item.author,
                    isbn=item.isbn,
                    subject=item.subject
                )

                try:
                    candidates, provider_statuses = await aggregate_and_rank_candidates_with_status(query)
                    item.provider_statuses = provider_statuses
                    item.results_count = len(candidates)

                    if candidates:
                        top = candidates[0]
                        item.top_candidate = top

                        # Classify access option & perform automatic acquisition if legally authorized
                        if top.licensing.is_legally_downloadable:
                            item.access_classification = "DOWNLOADABLE"
                            if top.pdf_url or top.download_url:
                                try:
                                    dl_job = await safe_downloader.execute_download(
                                        candidate=top,
                                        simulate_only=False,
                                        format="PDF",
                                        syllabus_name=syl_filename,
                                        semester=syl_semester,
                                        subject_name=item.subject
                                    )
                                    if dl_job.status in (DownloadJobStatus.COMPLETED, DownloadJobStatus.DUPLICATE):
                                        item.is_downloaded = True
                                        item.download_job_id = dl_job.job_id
                                        item.download_format = "PDF"
                                        item.download_path = dl_job.file_path
                                        item.download_size_bytes = dl_job.file_size_bytes
                                        item.download_hash = dl_job.file_hash
                                        logger.info(f"Auto-acquired verified book '{item.title}' (size: {dl_job.file_size_bytes} bytes, path: {dl_job.file_path})")
                                except Exception as dl_err:
                                    logger.warning(f"Auto-acquisition for '{item.title}' encountered: {dl_err}")
                        elif top.access_type == "FULL_TEXT":
                            item.access_classification = "FULL_TEXT"
                        elif top.access_type == "PREVIEW":
                            item.access_classification = "PREVIEW"
                        elif "archive.org" in (top.reader_url or "") and "borrow" in (top.access_message or "").lower():
                            item.access_classification = "BORROW"
                        elif top.licensing.status in (LicenseStatus.COMMERCIAL_RESTRICTED, LicenseStatus.NOT_ELIGIBLE):
                            item.access_classification = "NOT_ELIGIBLE"
                        else:
                            item.access_classification = "UNVERIFIED"

                        item.status = "COMPLETED"
                    else:
                        item.status = "NO_RESULTS"
                        item.access_classification = "NO_RESULTS"
                        item.error_message = "No matching volumes found across consulted providers."

                except Exception as e:
                    logger.error(f"Error searching book '{item.title}': {e}")
                    item.status = "FAILED"
                    item.access_classification = "ERROR"
                    item.error_message = str(e)

                repository.update_batch_book_item(item)

        # Execute all searches concurrently up to the semaphore limit
        tasks = [asyncio.create_task(_search_single_book(item)) for item in items]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info(f"Batch '{batch_id}' asyncio task was cancelled.")

        # Compute final totals
        all_items = repository.get_batch_book_items(batch_id)
        completed = sum(1 for it in all_items if it.status in ("COMPLETED", "NO_RESULTS"))
        failed = sum(1 for it in all_items if it.status == "FAILED")
        acquired = sum(1 for it in all_items if it.is_downloaded)
        is_cancelled = batch_id in self._cancelled_batches

        final_status = "CANCELLED" if is_cancelled else ("COMPLETED" if completed + failed == len(all_items) else "RUNNING")
        repository.update_search_batch_status(
            batch_id=batch_id,
            status=final_status,
            completed_books=completed,
            failed_books=failed,
            acquired_books=acquired
        )
        self._running_tasks.pop(batch_id, None)
        self._cancelled_batches.discard(batch_id)
        logger.info(f"Finished processing batch '{batch_id}' (Status: {final_status}, Acquired PDFs: {acquired}).")

    def get_batch_status(self, batch_id: str, access_filter: Optional[str] = None) -> Optional[BatchSearchStatusResponse]:
        """Retrieve full status, counts, and book items with optional filtering."""
        batch = repository.get_search_batch(batch_id)
        if not batch:
            return None

        books = repository.get_batch_book_items(batch_id)

        # Apply access filter if requested
        if access_filter and access_filter.upper() != "ALL":
            f_upper = access_filter.upper()
            if f_upper == "FREE_FULL_TEXT":
                books = [b for b in books if b.access_classification in ("FULL_TEXT", "DOWNLOADABLE")]
            elif f_upper == "DOWNLOADABLE":
                books = [b for b in books if b.access_classification == "DOWNLOADABLE"]
            elif f_upper == "PREVIEW":
                books = [b for b in books if b.access_classification == "PREVIEW"]
            elif f_upper == "BORROW":
                books = [b for b in books if b.access_classification == "BORROW"]
            elif f_upper == "NOT_ELIGIBLE":
                books = [b for b in books if b.access_classification in ("NOT_ELIGIBLE", "COMMERCIAL_RESTRICTED")]
            elif f_upper == "NO_RESULTS":
                books = [b for b in books if b.access_classification == "NO_RESULTS"]
            elif f_upper == "FAILED":
                books = [b for b in books if b.status == "FAILED"]
            elif f_upper == "IN_PROGRESS":
                books = [b for b in books if b.status in ("PENDING", "SEARCHING")]

        total = batch["total_books"]
        completed = batch["completed_books"]
        acquired = batch.get("acquired_books", 0)
        pct = round((completed / total * 100.0) if total > 0 else 0.0, 1)

        return BatchSearchStatusResponse(
            batch_id=batch["id"],
            syllabus_id=batch["syllabus_id"],
            total_books=total,
            completed_books=completed,
            failed_books=batch["failed_books"],
            acquired_books=acquired,
            progress_percentage=pct,
            status=batch["status"],
            books=books,
            created_at=batch["created_at"],
            updated_at=batch["updated_at"]
        )


batch_orchestrator = BatchOrchestrator()
