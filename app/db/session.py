import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from app.config import settings

logger = logging.getLogger(__name__)

_initialized_dbs = set()


def init_db():
    """Initialize database tables with schema migrations."""
    db_file = str(settings.db_path)
    if db_file in _initialized_dbs:
        return

    settings.storage_path.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA temp_store = MEMORY;")
    try:
        # Search Requests table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_requests (
                id TEXT PRIMARY KEY,
                query_json TEXT NOT NULL,
                candidate_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Candidates table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                search_id TEXT,
                title TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                download_url TEXT,
                licensing_status TEXT NOT NULL,
                is_legally_downloadable INTEGER NOT NULL,
                confidence_score REAL NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Approvals table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                snapshot_hash TEXT NOT NULL,
                book_title TEXT NOT NULL,
                book_authors_json TEXT NOT NULL,
                licensing_status TEXT NOT NULL,
                is_legally_downloadable INTEGER NOT NULL,
                approved_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                user_note TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)

        # Download Jobs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS download_jobs (
                job_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                approval_id TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                file_path TEXT,
                file_hash TEXT,
                file_size_bytes INTEGER,
                page_count INTEGER,
                error_message TEXT,
                provenance_json TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)

        # Provenance & Hash Registry table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS provenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE NOT NULL,
                candidate_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Syllabus Uploads table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS syllabus_uploads (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                page_count INTEGER,
                university TEXT,
                department TEXT,
                programme TEXT,
                semester TEXT,
                academic_year TEXT,
                extracted_subjects_json TEXT NOT NULL,
                status TEXT NOT NULL,
                raw_text TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Extracted Books table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extracted_books (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                edition TEXT,
                year INTEGER,
                publisher TEXT,
                isbn TEXT,
                book_type TEXT NOT NULL DEFAULT 'TEXTBOOK',
                subject TEXT,
                subject_code TEXT,
                page_number INTEGER,
                context_snippet TEXT,
                confidence REAL NOT NULL DEFAULT 0.85,
                is_selected INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (syllabus_id) REFERENCES syllabus_uploads(id) ON DELETE CASCADE
            )
        """)

        # Search Batches table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_batches (
                id TEXT PRIMARY KEY,
                syllabus_id TEXT,
                total_books INTEGER NOT NULL,
                completed_books INTEGER NOT NULL DEFAULT 0,
                failed_books INTEGER NOT NULL DEFAULT 0,
                acquired_books INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Batch Book Searches table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS batch_book_searches (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                extracted_book_id TEXT NOT NULL,
                search_id TEXT,
                title TEXT NOT NULL,
                author TEXT,
                isbn TEXT,
                subject TEXT,
                status TEXT NOT NULL,
                results_count INTEGER NOT NULL DEFAULT 0,
                top_candidate_id TEXT,
                top_candidate_json TEXT,
                access_classification TEXT NOT NULL DEFAULT 'UNVERIFIED',
                provider_statuses_json TEXT,
                error_message TEXT,
                is_downloaded INTEGER NOT NULL DEFAULT 0,
                download_job_id TEXT,
                download_format TEXT,
                download_path TEXT,
                download_size_bytes INTEGER,
                download_hash TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (batch_id) REFERENCES search_batches(id) ON DELETE CASCADE
            )
        """)

        # Migrations for existing databases
        for col, ctype in [
            ("university", "TEXT"),
            ("department", "TEXT"),
            ("programme", "TEXT"),
            ("semester", "TEXT"),
            ("academic_year", "TEXT")
        ]:
            try:
                cur.execute(f"ALTER TABLE syllabus_uploads ADD COLUMN {col} {ctype}")
            except Exception:
                pass

        try:
            cur.execute("ALTER TABLE extracted_books ADD COLUMN subject_code TEXT")
        except Exception:
            pass

        for col, ctype in [
            ("acquired_books", "INTEGER NOT NULL DEFAULT 0")
        ]:
            try:
                cur.execute(f"ALTER TABLE search_batches ADD COLUMN {col} {ctype}")
            except Exception:
                pass

        for col, ctype in [
            ("is_downloaded", "INTEGER NOT NULL DEFAULT 0"),
            ("download_job_id", "TEXT"),
            ("download_format", "TEXT"),
            ("download_path", "TEXT"),
            ("download_size_bytes", "INTEGER"),
            ("download_hash", "TEXT")
        ]:
            try:
                cur.execute(f"ALTER TABLE batch_book_searches ADD COLUMN {col} {ctype}")
            except Exception:
                pass

        cur.execute("CREATE INDEX IF NOT EXISTS idx_candidates_search ON candidates(search_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_approvals_candidate ON approvals(candidate_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_provenance_hash ON provenance_records(file_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_extracted_syllabus ON extracted_books(syllabus_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_batch_books ON batch_book_searches(batch_id)")

        conn.commit()
        _initialized_dbs.add(db_file)
        logger.info(f"Database tables initialized at {db_file}")
    finally:
        conn.close()


def get_connection() -> sqlite3.Connection:
    """Create a connection with row factory enabled, ensuring tables exist."""
    init_db()
    db_file = settings.db_path
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    """Context manager for safe database transactions."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
