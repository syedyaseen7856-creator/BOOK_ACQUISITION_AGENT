import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.db.session import db_cursor
from app.schemas import (
    BookCandidate,
    BookSearchQuery,
    ApprovalRecord,
    DownloadJob,
    DownloadJobStatus,
    LicenseStatus,
    ExtractedBookRecord,
    BookType,
    BatchBookItem,
    ProviderStatus,
    AcquisitionHistoryItem,
    DownloadLibraryItem
)

logger = logging.getLogger(__name__)


class Repository:
    """Repository handling all SQLite persistence operations."""

    def save_search(self, search_id: str, query: BookSearchQuery, candidates: List[BookCandidate]) -> None:
        """Persist a search request and all its ranked candidates."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO search_requests (id, query_json, candidate_count, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (search_id, json.dumps(query.model_dump()), len(candidates), now_iso)
            )

            for cand in candidates:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO candidates (
                        candidate_id, search_id, title, authors_json, source_name, source_url,
                        download_url, licensing_status, is_legally_downloadable, confidence_score,
                        data_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cand.candidate_id,
                        search_id,
                        cand.title,
                        json.dumps(cand.authors),
                        cand.source_name,
                        cand.source_url,
                        cand.download_url,
                        cand.licensing.status.value,
                        1 if cand.licensing.is_legally_downloadable else 0,
                        cand.confidence.total_score if cand.confidence else 0.0,
                        json.dumps(cand.model_dump()),
                        now_iso
                    )
                )

    def get_candidate(self, candidate_id: str) -> Optional[BookCandidate]:
        """Retrieve a specific candidate by ID."""
        with db_cursor() as cur:
            cur.execute("SELECT data_json FROM candidates WHERE candidate_id = ?", (candidate_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = json.loads(row["data_json"])
            return BookCandidate.model_validate(data)

    def save_approval(self, record: ApprovalRecord) -> None:
        """Persist an explicit candidate approval record."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO approvals (
                    approval_id, candidate_id, source_url, snapshot_hash, book_title,
                    book_authors_json, licensing_status, is_legally_downloadable,
                    approved_at, expires_at, user_note, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.approval_id,
                    record.candidate_id,
                    record.source_url,
                    record.snapshot_hash,
                    record.book_title,
                    json.dumps(record.book_authors),
                    record.licensing_status.value,
                    1 if record.is_legally_downloadable else 0,
                    record.approved_at,
                    record.expires_at,
                    record.user_note,
                    1 if record.is_active else 0
                )
            )

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        """Fetch approval by ID and verify expiration status."""
        with db_cursor() as cur:
            cur.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,))
            row = cur.fetchone()
            if not row:
                return None

            now = datetime.now(timezone.utc)
            expires = datetime.fromisoformat(row["expires_at"])
            is_expired = now >= expires or (row["is_active"] == 0)

            return ApprovalRecord(
                approval_id=row["approval_id"],
                candidate_id=row["candidate_id"],
                source_url=row["source_url"],
                snapshot_hash=row["snapshot_hash"],
                book_title=row["book_title"],
                book_authors=json.loads(row["book_authors_json"]),
                licensing_status=LicenseStatus(row["licensing_status"]),
                is_legally_downloadable=bool(row["is_legally_downloadable"]),
                approved_at=row["approved_at"],
                expires_at=row["expires_at"],
                is_expired=is_expired,
                user_note=row["user_note"],
                is_active=bool(row["is_active"])
            )

    def get_active_approval_for_candidate(self, candidate_id: str) -> Optional[ApprovalRecord]:
        """Fetch the latest active, non-expired approval for a candidate."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT approval_id FROM approvals
                WHERE candidate_id = ? AND is_active = 1
                ORDER BY approved_at DESC LIMIT 1
                """,
                (candidate_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self.get_approval(row["approval_id"])

    def list_approvals(self) -> List[ApprovalRecord]:
        """List all stored approval records with expiration evaluation."""
        records: List[ApprovalRecord] = []
        with db_cursor() as cur:
            cur.execute("SELECT approval_id FROM approvals ORDER BY approved_at DESC")
            rows = cur.fetchall()
            for r in rows:
                appr = self.get_approval(r["approval_id"])
                if appr:
                    records.append(appr)
        return records

    def create_download_job(self, job: DownloadJob) -> None:
        """Create a new download execution job record."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO download_jobs (
                    job_id, candidate_id, approval_id, status, progress,
                    file_path, file_hash, file_size_bytes, page_count,
                    error_message, provenance_json, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.candidate_id,
                    job.approval_id,
                    job.status.value,
                    job.progress,
                    job.file_path,
                    job.file_hash,
                    job.file_size_bytes,
                    job.page_count,
                    job.error_message,
                    json.dumps(job.provenance) if job.provenance else None,
                    job.created_at,
                    job.completed_at
                )
            )

    def update_download_job(self, job: DownloadJob) -> None:
        """Update job progress, file details, or error state."""
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE download_jobs SET
                    status = ?,
                    progress = ?,
                    file_path = ?,
                    file_hash = ?,
                    file_size_bytes = ?,
                    page_count = ?,
                    error_message = ?,
                    provenance_json = ?,
                    completed_at = ?
                WHERE job_id = ?
                """,
                (
                    job.status.value,
                    job.progress,
                    job.file_path,
                    job.file_hash,
                    job.file_size_bytes,
                    job.page_count,
                    job.error_message,
                    json.dumps(job.provenance) if job.provenance else None,
                    job.completed_at,
                    job.job_id
                )
            )

    def get_download_job(self, job_id: str) -> Optional[DownloadJob]:
        """Retrieve download job by ID."""
        with db_cursor() as cur:
            cur.execute("SELECT * FROM download_jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            return DownloadJob(
                job_id=row["job_id"],
                candidate_id=row["candidate_id"],
                approval_id=row["approval_id"],
                status=DownloadJobStatus(row["status"]),
                progress=row["progress"],
                file_path=row["file_path"],
                file_hash=row["file_hash"],
                file_size_bytes=row["file_size_bytes"],
                page_count=row["page_count"],
                error_message=row["error_message"],
                provenance=json.loads(row["provenance_json"]) if row["provenance_json"] else None,
                created_at=row["created_at"],
                completed_at=row["completed_at"]
            )

    def get_job_by_approval_id(self, approval_id: str) -> Optional[DownloadJob]:
        """Retrieve the latest download job associated with an approval."""
        with db_cursor() as cur:
            cur.execute(
                "SELECT * FROM download_jobs WHERE approval_id = ? ORDER BY created_at DESC LIMIT 1",
                (approval_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return DownloadJob(
                job_id=row["job_id"],
                candidate_id=row["candidate_id"],
                approval_id=row["approval_id"],
                status=DownloadJobStatus(row["status"]),
                progress=row["progress"],
                file_path=row["file_path"],
                file_hash=row["file_hash"],
                file_size_bytes=row["file_size_bytes"],
                page_count=row["page_count"],
                error_message=row["error_message"],
                provenance=json.loads(row["provenance_json"]) if row["provenance_json"] else None,
                created_at=row["created_at"],
                completed_at=row["completed_at"]
            )

    def find_provenance_by_hash(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        """Check if a file with this exact SHA-256 hash already exists in provenance database."""
        with db_cursor() as cur:
            cur.execute("SELECT provenance_json FROM provenance_records WHERE file_hash = ?", (sha256_hash,))
            row = cur.fetchone()
            if not row:
                return None
            return json.loads(row["provenance_json"])

    def save_provenance(self, file_hash: str, candidate_id: str, job_id: str, file_path: str, provenance: Dict[str, Any]) -> None:
        """Register a verified file hash in the provenance database for duplicate tracking."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO provenance_records (
                    file_hash, candidate_id, job_id, file_path, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_hash, candidate_id, job_id, file_path, json.dumps(provenance), now_iso)
            )

    def get_stats(self) -> Dict[str, int]:
        """Count totals for searches, approvals, and completed downloads."""
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM search_requests")
            searches = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM approvals WHERE is_active = 1")
            approvals = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM provenance_records")
            downloads = cur.fetchone()["c"]

            return {
                "searches": searches,
                "approvals": approvals,
                "downloads": downloads
            }

    # ==========================================
    # Syllabus Upload & Extracted Books Persistence
    # ==========================================

    def save_syllabus_upload(
        self,
        syllabus_id: str,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        page_count: Optional[int],
        extracted_subjects: List[str],
        raw_text: Optional[str] = None,
        university: Optional[str] = None,
        department: Optional[str] = None,
        programme: Optional[str] = None,
        semester: Optional[str] = None,
        academic_year: Optional[str] = None
    ) -> None:
        """Persist a syllabus upload record with academic metadata."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO syllabus_uploads (
                    id, filename, file_type, file_size_bytes, page_count,
                    university, department, programme, semester, academic_year,
                    extracted_subjects_json, status, raw_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    syllabus_id,
                    filename,
                    file_type,
                    file_size_bytes,
                    page_count,
                    university,
                    department,
                    programme,
                    semester,
                    academic_year,
                    json.dumps(extracted_subjects),
                    "EXTRACTED",
                    raw_text,
                    now_iso
                )
            )

    def get_syllabus_upload(self, syllabus_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a syllabus upload record by ID."""
        with db_cursor() as cur:
            cur.execute("SELECT * FROM syllabus_uploads WHERE id = ?", (syllabus_id,))
            row = cur.fetchone()
            if not row:
                return None
            r_keys = row.keys()
            return {
                "id": row["id"],
                "filename": row["filename"],
                "file_type": row["file_type"],
                "file_size_bytes": row["file_size_bytes"],
                "page_count": row["page_count"],
                "university": row["university"] if "university" in r_keys else None,
                "department": row["department"] if "department" in r_keys else None,
                "programme": row["programme"] if "programme" in r_keys else None,
                "semester": row["semester"] if "semester" in r_keys else None,
                "academic_year": row["academic_year"] if "academic_year" in r_keys else None,
                "extracted_subjects": json.loads(row["extracted_subjects_json"]),
                "status": row["status"],
                "created_at": row["created_at"]
            }

    def save_extracted_books(self, books: List[ExtractedBookRecord]) -> None:
        """Persist a list of extracted book records with subject code."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            for b in books:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO extracted_books (
                        id, syllabus_id, title, author, edition, year, publisher,
                        isbn, book_type, subject, subject_code, page_number, context_snippet,
                        confidence, is_selected, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        b.id,
                        b.syllabus_id,
                        b.title,
                        b.author,
                        b.edition,
                        b.year,
                        b.publisher,
                        b.isbn,
                        b.book_type.value if hasattr(b.book_type, "value") else str(b.book_type),
                        b.subject,
                        b.subject_code,
                        b.page_number,
                        b.context_snippet,
                        b.confidence,
                        1 if b.is_selected else 0,
                        b.created_at or now_iso
                    )
                )

    def get_extracted_books(self, syllabus_id: str) -> List[ExtractedBookRecord]:
        """Fetch all extracted books for a given syllabus."""
        with db_cursor() as cur:
            cur.execute(
                "SELECT * FROM extracted_books WHERE syllabus_id = ? ORDER BY rowid ASC",
                (syllabus_id,)
            )
            rows = cur.fetchall()
            books: List[ExtractedBookRecord] = []
            for r in rows:
                b_type = BookType(r["book_type"]) if r["book_type"] in [e.value for e in BookType] else BookType.TEXTBOOK
                r_keys = r.keys()
                books.append(
                    ExtractedBookRecord(
                        id=r["id"],
                        syllabus_id=r["syllabus_id"],
                        title=r["title"],
                        author=r["author"],
                        edition=r["edition"],
                        year=r["year"],
                        publisher=r["publisher"],
                        isbn=r["isbn"],
                        book_type=b_type,
                        subject=r["subject"],
                        subject_code=r["subject_code"] if "subject_code" in r_keys else None,
                        page_number=r["page_number"],
                        context_snippet=r["context_snippet"],
                        confidence=float(r["confidence"]),
                        is_selected=bool(r["is_selected"]),
                        created_at=r["created_at"]
                    )
                )
            return books

    def update_extracted_books(self, syllabus_id: str, books: List[ExtractedBookRecord]) -> None:
        """Replace/update extracted books for a syllabus."""
        with db_cursor() as cur:
            cur.execute("DELETE FROM extracted_books WHERE syllabus_id = ?", (syllabus_id,))
        self.save_extracted_books(books)

    def add_extracted_book(self, book: ExtractedBookRecord) -> None:
        """Add a single extracted book record."""
        self.save_extracted_books([book])

    def delete_extracted_book(self, book_id: str) -> None:
        """Delete an extracted book by ID."""
        with db_cursor() as cur:
            cur.execute("DELETE FROM extracted_books WHERE id = ?", (book_id,))

    # ==========================================
    # Batch Search Persistence
    # ==========================================

    def create_search_batch(self, batch_id: str, syllabus_id: Optional[str], total_books: int) -> None:
        """Initialize a new batch search."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO search_batches (
                    id, syllabus_id, total_books, completed_books, failed_books,
                    acquired_books, status, created_at, updated_at
                ) VALUES (?, ?, ?, 0, 0, 0, ?, ?, ?)
                """,
                (batch_id, syllabus_id, total_books, "PENDING", now_iso, now_iso)
            )

    def get_search_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Fetch batch summary."""
        with db_cursor() as cur:
            cur.execute("SELECT * FROM search_batches WHERE id = ?", (batch_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "syllabus_id": row["syllabus_id"],
                "total_books": row["total_books"],
                "completed_books": row["completed_books"],
                "failed_books": row["failed_books"],
                "acquired_books": row["acquired_books"] if "acquired_books" in row.keys() else 0,
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def update_search_batch_status(
        self,
        batch_id: str,
        status: str,
        completed_books: Optional[int] = None,
        failed_books: Optional[int] = None,
        acquired_books: Optional[int] = None
    ) -> None:
        """Update batch progress and completion status."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            fields = ["status = ?", "updated_at = ?"]
            params = [status, now_iso]

            if completed_books is not None:
                fields.append("completed_books = ?")
                params.append(completed_books)
            if failed_books is not None:
                fields.append("failed_books = ?")
                params.append(failed_books)
            if acquired_books is not None:
                fields.append("acquired_books = ?")
                params.append(acquired_books)

            params.append(batch_id)
            query = f"UPDATE search_batches SET {', '.join(fields)} WHERE id = ?"
            cur.execute(query, tuple(params))

    def add_batch_book_item(self, item: BatchBookItem) -> None:
        """Insert a book entry into a search batch."""
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO batch_book_searches (
                    id, batch_id, extracted_book_id, search_id, title, author,
                    isbn, subject, status, results_count, top_candidate_id,
                    top_candidate_json, access_classification, provider_statuses_json,
                    error_message, is_downloaded, download_job_id, download_format,
                    download_path, download_size_bytes, download_hash, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.batch_id,
                    item.extracted_book_id,
                    None,
                    item.title,
                    item.author,
                    item.isbn,
                    item.subject,
                    item.status,
                    item.results_count,
                    item.top_candidate.candidate_id if item.top_candidate else None,
                    json.dumps(item.top_candidate.model_dump()) if item.top_candidate else None,
                    item.access_classification,
                    json.dumps([p.model_dump() for p in item.provider_statuses]),
                    item.error_message,
                    1 if item.is_downloaded else 0,
                    item.download_job_id,
                    item.download_format,
                    item.download_path,
                    item.download_size_bytes,
                    item.download_hash,
                    item.updated_at
                )
            )

    def update_batch_book_item(self, item: BatchBookItem) -> None:
        """Update a batch book search outcome."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE batch_book_searches SET
                    status = ?, results_count = ?, top_candidate_id = ?,
                    top_candidate_json = ?, access_classification = ?,
                    provider_statuses_json = ?, error_message = ?,
                    is_downloaded = ?, download_job_id = ?, download_format = ?,
                    download_path = ?, download_size_bytes = ?, download_hash = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    item.status,
                    item.results_count,
                    item.top_candidate.candidate_id if item.top_candidate else None,
                    json.dumps(item.top_candidate.model_dump()) if item.top_candidate else None,
                    item.access_classification,
                    json.dumps([p.model_dump() for p in item.provider_statuses]),
                    item.error_message,
                    1 if item.is_downloaded else 0,
                    item.download_job_id,
                    item.download_format,
                    item.download_path,
                    item.download_size_bytes,
                    item.download_hash,
                    now_iso,
                    item.id
                )
            )

    def get_batch_book_items(self, batch_id: str) -> List[BatchBookItem]:
        """Fetch all books associated with a batch search."""
        items: List[BatchBookItem] = []
        with db_cursor() as cur:
            cur.execute(
                "SELECT * FROM batch_book_searches WHERE batch_id = ? ORDER BY rowid ASC",
                (batch_id,)
            )
            rows = cur.fetchall()
            for r in rows:
                top_cand = None
                if r["top_candidate_json"]:
                    try:
                        top_cand = BookCandidate.model_validate(json.loads(r["top_candidate_json"]))
                    except Exception:
                        pass

                providers = []
                if r["provider_statuses_json"]:
                    try:
                        providers = [ProviderStatus.model_validate(p) for p in json.loads(r["provider_statuses_json"])]
                    except Exception:
                        pass

                r_keys = r.keys()
                is_dl = bool(r["is_downloaded"]) if "is_downloaded" in r_keys else False
                dl_job = r["download_job_id"] if "download_job_id" in r_keys else None
                dl_fmt = r["download_format"] if "download_format" in r_keys else None
                dl_path = r["download_path"] if "download_path" in r_keys else None
                dl_size = r["download_size_bytes"] if "download_size_bytes" in r_keys else None
                dl_hash = r["download_hash"] if "download_hash" in r_keys else None

                items.append(
                    BatchBookItem(
                        id=r["id"],
                        batch_id=r["batch_id"],
                        extracted_book_id=r["extracted_book_id"],
                        title=r["title"],
                        author=r["author"],
                        isbn=r["isbn"],
                        subject=r["subject"],
                        status=r["status"],
                        results_count=r["results_count"],
                        top_candidate=top_cand,
                        access_classification=r["access_classification"],
                        provider_statuses=providers,
                        error_message=r["error_message"],
                        is_downloaded=is_dl,
                        download_job_id=dl_job,
                        download_format=dl_fmt,
                        download_path=dl_path,
                        download_size_bytes=dl_size,
                        download_hash=dl_hash,
                        updated_at=r["updated_at"]
                    )
                )
        return items

    # ==========================================
    # Consolidated Acquisition & Audit History
    # ==========================================

    def get_acquisition_history(
        self,
        record_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[AcquisitionHistoryItem]:
        """
        Retrieve unified audit log across searches, approvals, and downloads.
        """
        history: List[AcquisitionHistoryItem] = []

        with db_cursor() as cur:
            # 1. Download Provenance
            if not record_type or record_type.upper() == "DOWNLOAD":
                cur.execute(
                    """
                    SELECT p.file_hash, p.candidate_id, p.job_id, p.created_at,
                           c.title, c.authors_json, c.source_name
                    FROM provenance_records p
                    LEFT JOIN candidates c ON p.candidate_id = c.candidate_id
                    ORDER BY p.created_at DESC LIMIT ?
                    """,
                    (limit,)
                )
                for r in cur.fetchall():
                    authors = json.loads(r["authors_json"]) if r["authors_json"] else []
                    history.append(
                        AcquisitionHistoryItem(
                            id=f"hist_dl_{r['job_id']}",
                            record_type="DOWNLOAD",
                            title=r["title"] or "Acquired Document",
                            author=", ".join(authors) if authors else "Unknown",
                            source=r["source_name"] or "Authorized Repository",
                            status="COMPLETED",
                            timestamp=r["created_at"],
                            details={"candidate_id": r["candidate_id"], "job_id": r["job_id"]},
                            file_hash=r["file_hash"]
                        )
                    )

            # 2. Approvals
            if not record_type or record_type.upper() == "APPROVAL":
                cur.execute(
                    """
                    SELECT approval_id, candidate_id, book_title, book_authors_json,
                           source_url, licensing_status, approved_at, expires_at,
                           snapshot_hash, is_active
                    FROM approvals
                    ORDER BY approved_at DESC LIMIT ?
                    """,
                    (limit,)
                )
                for r in cur.fetchall():
                    authors = json.loads(r["book_authors_json"]) if r["book_authors_json"] else []
                    history.append(
                        AcquisitionHistoryItem(
                            id=f"hist_appr_{r['approval_id']}",
                            record_type="APPROVAL",
                            title=r["book_title"],
                            author=", ".join(authors) if authors else "Unknown",
                            source=r["source_url"],
                            status="ACTIVE" if r["is_active"] else "EXPIRED",
                            timestamp=r["approved_at"],
                            details={
                                "licensing_status": r["licensing_status"],
                                "snapshot_hash": r["snapshot_hash"],
                                "expires_at": r["expires_at"]
                            }
                        )
                    )

            # 3. Searches
            if not record_type or record_type.upper() == "SEARCH":
                cur.execute(
                    """
                    SELECT id, query_json, candidate_count, created_at
                    FROM search_requests
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (limit,)
                )
                for r in cur.fetchall():
                    q_data = json.loads(r["query_json"]) if r["query_json"] else {}
                    title = q_data.get("title") or q_data.get("q") or "Catalog Search"
                    author = q_data.get("author")
                    history.append(
                        AcquisitionHistoryItem(
                            id=f"hist_srch_{r['id']}",
                            record_type="SEARCH",
                            title=title,
                            author=author,
                            source="Multi-Provider Search",
                            status="COMPLETED" if r["candidate_count"] > 0 else "NO_RESULTS",
                            timestamp=r["created_at"],
                            details={"candidate_count": r["candidate_count"], "query": q_data}
                        )
                    )

        # Sort combined history by timestamp descending
        history.sort(key=lambda h: h.timestamp, reverse=True)
        if status:
            history = [h for h in history if h.status.upper() == status.upper()]
        return history[:limit]

    # ==========================================
    # Download Library Records
    # ==========================================

    def get_download_library_items(self) -> List[DownloadLibraryItem]:
        """Fetch all verified acquired books stored in the download library."""
        items: List[DownloadLibraryItem] = []
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT p.file_hash, p.candidate_id, p.job_id, p.file_path, p.provenance_json, p.created_at,
                       c.title AS c_title, c.authors_json AS c_authors, c.source_name AS c_source
                FROM provenance_records p
                LEFT JOIN candidates c ON p.candidate_id = c.candidate_id
                ORDER BY p.created_at DESC
                """
            )
            rows = cur.fetchall()
            for r in rows:
                prov = json.loads(r["provenance_json"]) if r["provenance_json"] else {}
                title = prov.get("title") or r["c_title"] or "Acquired Book"
                authors = prov.get("authors") or (json.loads(r["c_authors"]) if r["c_authors"] else [])
                file_path = prov.get("file_path") or r["file_path"]
                file_size = prov.get("file_size_bytes") or 0
                provider = prov.get("source_name") or r["c_source"] or "Authorized Repository"
                edition = prov.get("edition")
                publisher = prov.get("publisher")
                subject = prov.get("subject_name")
                syllabus_name = prov.get("syllabus_name")
                semester = prov.get("semester")
                fmt = prov.get("format") or ("EPUB" if str(file_path).lower().endswith(".epub") else "PDF")

                items.append(
                    DownloadLibraryItem(
                        id=f"lib_{r['job_id']}",
                        job_id=r["job_id"],
                        candidate_id=r["candidate_id"],
                        title=title,
                        authors=authors if isinstance(authors, list) else [str(authors)],
                        edition=edition,
                        publisher=publisher,
                        subject=subject,
                        syllabus_name=syllabus_name,
                        semester=semester,
                        provider=provider,
                        format=fmt.upper(),
                        file_path=str(file_path),
                        file_size_bytes=int(file_size),
                        file_hash=r["file_hash"],
                        status="VERIFIED",
                        downloaded_at=r["created_at"]
                    )
                )
        return items

    def delete_download_library_item(self, job_id: str) -> bool:
        """Delete a download library file from disk and database."""
        from pathlib import Path
        with db_cursor() as cur:
            cur.execute("SELECT file_path FROM provenance_records WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if row and row["file_path"]:
                try:
                    f = Path(row["file_path"])
                    if f.exists():
                        f.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Could not delete physical file for job {job_id}: {e}")

            cur.execute("DELETE FROM provenance_records WHERE job_id = ?", (job_id,))
            cur.execute("DELETE FROM download_jobs WHERE job_id = ?", (job_id,))
            return True


repository = Repository()

