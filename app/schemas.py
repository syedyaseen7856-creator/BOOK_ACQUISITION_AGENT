from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LicenseStatus(str, Enum):
    VERIFIED_FOR_PERMITTED_DOWNLOAD = "VERIFIED_FOR_PERMITTED_DOWNLOAD"
    COMMERCIAL_RESTRICTED = "COMMERCIAL_RESTRICTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class ConfidenceTier(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"          # 90 - 100
    PLAUSIBLE_MATCH = "PLAUSIBLE_MATCH"    # 75 - 89
    LOW_CONFIDENCE = "LOW_CONFIDENCE"      # Below 75


class AccessState(str, Enum):
    AUTHORIZED_DOWNLOAD = "AUTHORIZED_DOWNLOAD"
    FULL_TEXT_ONLINE = "FULL_TEXT_ONLINE"
    PREVIEW_ONLY = "PREVIEW_ONLY"
    BORROWING_REQUIRED = "BORROWING_REQUIRED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    COMMERCIAL_ACCESS = "COMMERCIAL_ACCESS"
    RIGHTS_UNCLEAR = "RIGHTS_UNCLEAR"
    UNAVAILABLE = "UNAVAILABLE"


class AccessClassification(str, Enum):
    AUTHORIZED_FREE_PDF = "AUTHORIZED_FREE_PDF"
    AUTHORIZED_FREE_EPUB = "AUTHORIZED_FREE_EPUB"
    FULL_TEXT_READABLE_ONLINE_NO_DOWNLOAD = "FULL_TEXT_READABLE_ONLINE_NO_DOWNLOAD"
    LIMITED_PREVIEW = "LIMITED_PREVIEW"
    BORROWING_OR_LOGIN_REQUIRED = "BORROWING_OR_LOGIN_REQUIRED"
    COMMERCIAL_ACCESS_REQUIRED = "COMMERCIAL_ACCESS_REQUIRED"
    ACCESS_STATUS_UNKNOWN = "ACCESS_STATUS_UNKNOWN"
    NO_READABLE_COPY_FOUND = "NO_READABLE_COPY_FOUND"


class LicensingEvidence(BaseModel):
    status: LicenseStatus = Field(
        ...,
        description="Independent legal licensing verification state."
    )
    license_name: str = Field(
        ...,
        description="Designation of license (e.g. Public Domain, CC-BY-NC 4.0, Commercial In-Copyright)."
    )
    rights_statement: str = Field(
        ...,
        description="Raw or declared rights statement text from repository metadata."
    )
    source_url: str = Field(
        ...,
        description="Canonical URL where rights metadata was verified."
    )
    terms_url: Optional[str] = Field(
        default=None,
        description="Direct link to repository license or terms of use."
    )
    evidence_details: List[str] = Field(
        default_factory=list,
        description="List of specific legal evidence factors evaluated."
    )
    verified_at: str = Field(
        ...,
        description="ISO-8601 timestamp of verification."
    )
    intended_use: str = Field(
        default="educational_reference_acquisition",
        description="Intended institutional or educational use scope."
    )
    is_legally_downloadable: bool = Field(
        default=False,
        description="Explicit boolean indicator if work is verified for authorized download."
    )


class ConfidenceBreakdown(BaseModel):
    total_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Overall deterministic Python Book Match Score (0 to 100)."
    )
    title_score: float = Field(..., ge=0.0, le=30.0, description="Title match component (max 30 pts).")
    author_score: float = Field(..., ge=0.0, le=25.0, description="Author match component (max 25 pts).")
    isbn_score: float = Field(..., ge=0.0, le=20.0, description="ISBN verification component (max 20 pts).")
    edition_year_score: float = Field(..., ge=0.0, le=15.0, description="Edition and publication year (max 15 pts).")
    publisher_score: float = Field(..., ge=0.0, le=10.0, description="Publisher match component (max 10 pts).")
    confidence_tier: ConfidenceTier = Field(
        ..., description="Standard presentation tier (STRONG_MATCH, PLAUSIBLE_MATCH, LOW_CONFIDENCE)."
    )
    evidence_used: List[str] = Field(
        default_factory=list, description="Metadata attributes used during evaluation."
    )
    missing_fields: List[str] = Field(
        default_factory=list, description="Query or candidate fields that were missing."
    )
    mismatches_and_uncertainty: List[str] = Field(
        default_factory=list, description="Conflicting fields, ISBN divergence, or year discrepancies."
    )
    explanation: List[str] = Field(
        default_factory=list, description="Detailed narrative explanation of the ranking calculation."
    )
    has_hard_mismatch: bool = Field(
        default=False, description="Flag indicating whether a conflicting ISBN or author was detected."
    )


class BookSearchQuery(BaseModel):
    q: Optional[str] = Field(default=None, description="Unified or general search query string.")
    title: Optional[str] = Field(default=None, description="Title of the book.")
    author: Optional[str] = Field(default=None, description="Author or editor name.")
    isbn: Optional[str] = Field(default=None, description="ISBN-10 or ISBN-13.")
    edition: Optional[str] = Field(default=None, description="Edition identifier (e.g. '3rd', 'First').")
    year: Optional[int] = Field(default=None, description="Publication year.")
    subject: Optional[str] = Field(default=None, description="Subject area or academic discipline.")
    use_mock_data: bool = Field(
        default=False,
        description="Whether to use offline mock candidates for deterministic testing."
    )

    def is_empty(self) -> bool:
        return not any([
            self.q and self.q.strip(),
            self.title and self.title.strip(),
            self.author and self.author.strip(),
            self.isbn and self.isbn.strip(),
            self.subject and self.subject.strip()
        ])


class ProviderStatus(BaseModel):
    provider_name: str = Field(..., description="Name of the metadata provider (e.g. Google Books, Open Library).")
    status: str = Field(..., description="Query outcome: 'SUCCESS', 'RATE_LIMITED', 'NO_RESULTS', 'ERROR', 'UNAVAILABLE', 'NOT_CONFIGURED', 'CIRCUIT_OPEN', 'CACHED'.")
    message: Optional[str] = Field(default=None, description="Detailed explanatory message or error cause.")
    results_count: int = Field(default=0, description="Number of candidate records returned.")
    elapsed_ms: Optional[float] = Field(default=None, description="Provider query latency in milliseconds.")
    cached: bool = Field(default=False, description="Whether the response was served from cache.")
    retry_after: Optional[int] = Field(default=None, description="Reported Retry-After interval in seconds if rate-limited.")


class BookCandidate(BaseModel):
    candidate_id: str = Field(..., description="Unique deterministic or provider identifier.")
    title: str = Field(..., description="Book title.")
    alternate_titles: List[str] = Field(default_factory=list, description="Alternate or translated titles.")
    subtitle: Optional[str] = Field(default=None, description="Book subtitle if provided by source.")
    authors: List[str] = Field(default_factory=list, description="List of author/creator names.")
    publisher: Optional[str] = Field(default=None, description="Publisher name.")
    published_date: Optional[str] = Field(default=None, description="Exact or full publication date string.")
    published_year: Optional[int] = Field(default=None, description="Year of publication.")
    edition: Optional[str] = Field(default=None, description="Edition string.")
    isbns: List[str] = Field(default_factory=list, description="Extracted ISBNs (10 or 13).")
    isbn_10: Optional[str] = Field(default=None, description="Identified ISBN-10.")
    isbn_13: Optional[str] = Field(default=None, description="Identified ISBN-13.")
    page_count: Optional[int] = Field(default=None, description="Total reported pages.")
    language: Optional[str] = Field(default="en", description="Language code.")
    categories: List[str] = Field(default_factory=list, description="Subjects, topics or academic disciplines.")
    description: Optional[str] = Field(default=None, description="Summary or syllabus description.")
    thumbnail_url: Optional[str] = Field(default=None, description="Cover image thumbnail URL.")
    source_name: str = Field(..., description="Provider source (Google Books, Open Library, Gutenberg, etc.).")
    source_url: str = Field(..., description="Canonical source URL on the repository.")
    reader_url: Optional[str] = Field(
        default=None,
        description="Direct verified URL for legitimate online reading or viewer."
    )
    embed_url: Optional[str] = Field(
        default=None,
        description="Direct verified URL suitable for safe in-app iframe embedding (e.g. Internet Archive BookReader, Google Books Embed)."
    )
    external_search_url: Optional[str] = Field(
        default=None,
        description="Clearly labelled external discovery link when direct download/reader API is unavailable."
    )
    preview_url: Optional[str] = Field(
        default=None,
        description="Legitimate preview URL if full text is unconfirmed or partial."
    )
    pdf_url: Optional[str] = Field(
        default=None,
        description="Direct verified PDF URL if authorized."
    )
    epub_url: Optional[str] = Field(
        default=None,
        description="Direct verified EPUB URL if authorized."
    )
    access_state: AccessState = Field(
        default=AccessState.UNAVAILABLE,
        description="Explicit 8-state access tier: AUTHORIZED_DOWNLOAD, FULL_TEXT_ONLINE, PREVIEW_ONLY, BORROWING_REQUIRED, LOGIN_REQUIRED, COMMERCIAL_ACCESS, RIGHTS_UNCLEAR, UNAVAILABLE."
    )
    access_classification: AccessClassification = Field(
        default=AccessClassification.ACCESS_STATUS_UNKNOWN,
        description="Granular access classification: AUTHORIZED_FREE_PDF, AUTHORIZED_FREE_EPUB, FULL_TEXT_READABLE_ONLINE_NO_DOWNLOAD, LIMITED_PREVIEW, BORROWING_OR_LOGIN_REQUIRED, COMMERCIAL_ACCESS_REQUIRED, ACCESS_STATUS_UNKNOWN, NO_READABLE_COPY_FOUND."
    )
    access_type: str = Field(
        default="UNAVAILABLE",
        description="Online access classification: 'FULL_TEXT', 'PREVIEW', 'PUBLISHER_PAGE', 'UNAVAILABLE'."
    )
    access_message: Optional[str] = Field(
        default=None,
        description="Truthful explanation of available online reading access."
    )
    reader_type: str = Field(
        default="NONE",
        description="Type of reading access: 'FULL_READER', 'EMBEDDED_PDF', 'HTML_READER', 'PREVIEW_ONLY', 'OFFICIAL_PAGE', 'NONE'."
    )
    can_embed: bool = Field(
        default=False,
        description="Whether the reader source allows in-app embedding without violating CSP or terms."
    )
    download_url: Optional[str] = Field(
        default=None,
        description="Direct download URL if authorized (NEVER accessed automatically)."
    )
    format: Optional[str] = Field(default="PDF", description="Format (PDF, EPUB, TXT, PREVIEW_ONLY).")
    is_open_access: bool = Field(
        default=False,
        description="Dual-path acquisition categorization: True for Path A (Direct Open-Access Downloads), False for Path B (Lending & Digital Preview Only)."
    )
    confidence: Optional[ConfidenceBreakdown] = Field(
        default=None, description="Computed explainable 0-100 confidence breakdown."
    )
    licensing: LicensingEvidence = Field(
        ..., description="Independently verified licensing evidence."
    )
    missing_or_conflicting_metadata: List[str] = Field(
        default_factory=list, description="Documented missing or conflicting metadata items."
    )
    is_approximate_suggestion: bool = Field(
        default=False, description="Flag indicating weak/partial keyword match rather than confident identity match."
    )
    is_demo_data: bool = Field(
        default=False, description="Flag indicating if candidate record is from the offline demo catalog."
    )
    match_type: Optional[str] = Field(
        default="EXACT_MATCH",
        description="Classification: 'EXACT_MATCH', 'ALTERNATE_EDITION', 'RELATED_PUBLICATION', 'UNRELATED'."
    )
    match_explanation: Optional[str] = Field(
        default=None,
        description="Clear narrative explanation of why this record matched the query."
    )

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_page_count

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict):
            if "is_open_access" not in obj:
                # Path A: OpenStax, DOAB, Gutenberg, or verified downloadable open-access PDF
                src = str(obj.get("source_name", "")).lower()
                is_target_oa_repo = any(r in src for r in ["openstax", "doab", "directory of open access books", "gutenberg"])
                has_download = bool(obj.get("download_url") or obj.get("pdf_url"))
                is_auth_dl = obj.get("access_state") == AccessState.AUTHORIZED_DOWNLOAD or obj.get("access_state") == "AUTHORIZED_DOWNLOAD"
                is_lic_dl = False
                lic = obj.get("licensing")
                if isinstance(lic, dict):
                    is_lic_dl = bool(lic.get("is_legally_downloadable"))
                elif hasattr(lic, "is_legally_downloadable"):
                    is_lic_dl = bool(lic.is_legally_downloadable)
                obj["is_open_access"] = bool((is_target_oa_repo and has_download) or (is_auth_dl and has_download) or (is_lic_dl and has_download))

            if "page_count" in obj:
                raw_p = obj["page_count"]
                if isinstance(raw_p, str):
                    import re
                    digits = re.findall(r"\d+", raw_p)
                    if digits:
                        if len(digits) >= 2 and "-" in raw_p:
                            try:
                                p1, p2 = int(digits[0]), int(digits[1])
                                if p2 >= p1:
                                    obj["page_count"] = p2 - p1 + 1
                                else:
                                    obj["page_count"] = int(digits[0])
                            except Exception:
                                obj["page_count"] = int(digits[0])
                        else:
                            obj["page_count"] = int(digits[0])
                    else:
                        obj["page_count"] = None
        return super().model_validate(obj, *args, **kwargs)


class SearchResponse(BaseModel):
    query: BookSearchQuery
    total_candidates: int
    candidates: List[BookCandidate]
    related_publications: List[BookCandidate] = Field(
        default_factory=list,
        description="Secondary publications, author biographies, critical companions, and related works."
    )
    total_related: int = Field(default=0, description="Total count of related publications.")
    provider_statuses: List[ProviderStatus] = Field(
        default_factory=list,
        description="Operational status of each metadata provider consulted during discovery."
    )


class CandidateApprovalRequest(BaseModel):
    user_affirmation: bool = Field(
        ...,
        description="Explicit user affirmation: must be true to authorize acquisition."
    )
    user_note: Optional[str] = Field(
        default=None,
        description="Optional librarian or syllabus reference justification."
    )


class ApprovalRecord(BaseModel):
    approval_id: str = Field(..., description="Unique approval identifier.")
    candidate_id: str = Field(..., description="ID of the approved candidate.")
    source_url: str = Field(..., description="Exact repository URL approved.")
    snapshot_hash: str = Field(..., description="SHA-256 hash of candidate metadata snapshot.")
    book_title: str
    book_authors: List[str]
    licensing_status: LicenseStatus
    is_legally_downloadable: bool
    approved_at: str
    expires_at: str
    is_expired: bool = False
    user_note: Optional[str] = None
    is_active: bool = True
    download_status: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    evidence_details: List[str] = Field(default_factory=list)


class DownloadJobStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    DUPLICATE = "DUPLICATE"


class DownloadJob(BaseModel):
    job_id: str
    candidate_id: str
    approval_id: str
    status: DownloadJobStatus
    progress: int = Field(default=0, ge=0, le=100)
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    created_at: str
    completed_at: Optional[str] = None


class SystemStatus(BaseModel):
    app_name: str
    version: str
    environment: str
    database_connected: bool
    gemini_flash_configured: bool
    gemini_model: str
    allowed_domains: List[str]
    max_file_size_mb: int
    approval_expiry_hours: int
    total_searches_recorded: int
    total_approvals_recorded: int
    total_downloads_recorded: int


# ==========================================
# Syllabus Extraction & Batch Search Models
# ==========================================

class BookType(str, Enum):
    TEXTBOOK = "TEXTBOOK"
    REFERENCE = "REFERENCE"
    SUGGESTED_READING = "SUGGESTED_READING"


class ExtractedBookRecord(BaseModel):
    id: str = Field(..., description="Unique ID for extracted book entry.")
    syllabus_id: str = Field(..., description="Associated syllabus upload ID.")
    title: str = Field(..., description="Extracted book title.")
    clean_title: Optional[str] = Field(default=None, description="Cleaned and normalized title stripped of publisher, edition, and year artifacts.")
    author: Optional[str] = Field(default=None, description="Extracted author(s) string.")
    authors: List[str] = Field(default_factory=list, description="Structured list of author names.")
    edition: Optional[str] = Field(default=None, description="Extracted edition string (e.g. '3rd ed.').")
    year: Optional[int] = Field(default=None, description="Publication year.")
    publisher: Optional[str] = Field(default=None, description="Publisher name.")
    isbn: Optional[str] = Field(default=None, description="Extracted ISBN-10 or ISBN-13.")
    book_type: BookType = Field(default=BookType.TEXTBOOK, description="Textbook, reference, or suggested reading.")
    priority_status: Optional[str] = Field(default="REQUIRED", description="Structured priority status: REQUIRED, RECOMMENDED, or OPTIONAL.")
    subject: Optional[str] = Field(default=None, description="Associated subject/course module.")
    subject_code: Optional[str] = Field(default=None, description="Course or subject code (e.g. CS301).")
    page_number: Optional[int] = Field(default=None, description="Syllabus page where reference was identified.")
    context_snippet: Optional[str] = Field(default=None, description="Raw citation or snippet from syllabus.")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Extraction confidence score.")
    is_selected: bool = Field(default=True, description="Whether book is selected for batch acquisition.")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp.")

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict):
            # Auto-populate clean_title if missing
            if not obj.get("clean_title") and obj.get("title"):
                obj["clean_title"] = obj["title"]
            # Auto-populate authors list if missing
            if not obj.get("authors") and obj.get("author"):
                author_str = str(obj["author"])
                import re
                parts = re.split(r",\s*(?:and\s+)?|\s+and\s+|&\s*", author_str)
                obj["authors"] = [p.strip() for p in parts if p.strip()]
            # Auto-populate priority_status based on book_type
            if not obj.get("priority_status"):
                b_type = obj.get("book_type")
                if b_type == BookType.TEXTBOOK or b_type == "TEXTBOOK":
                    obj["priority_status"] = "REQUIRED"
                elif b_type == BookType.REFERENCE or b_type == "REFERENCE":
                    obj["priority_status"] = "RECOMMENDED"
                else:
                    obj["priority_status"] = "OPTIONAL"
        return super().model_validate(obj, *args, **kwargs)


class SyllabusUploadResponse(BaseModel):
    syllabus_id: str = Field(..., description="Unique syllabus upload ID.")
    filename: str = Field(..., description="Uploaded file name.")
    file_type: str = Field(..., description="File format: PDF, DOCX, or TXT.")
    file_size_bytes: int = Field(..., description="File size in bytes.")
    page_count: Optional[int] = Field(default=None, description="Total pages in document.")
    university: Optional[str] = Field(default=None, description="Extracted university or college name.")
    department: Optional[str] = Field(default=None, description="Extracted academic department.")
    programme: Optional[str] = Field(default=None, description="Extracted degree or programme.")
    semester: Optional[str] = Field(default=None, description="Extracted semester.")
    academic_year: Optional[str] = Field(default=None, description="Extracted academic year.")
    extracted_subjects: List[str] = Field(default_factory=list, description="Course subjects detected.")
    books: List[ExtractedBookRecord] = Field(default_factory=list, description="Extracted reference books.")
    total_extracted: int = Field(default=0, description="Total books extracted.")
    status: str = Field(default="EXTRACTED", description="Upload/extraction status.")
    message: Optional[str] = Field(default=None, description="Summary or warning message.")


class SyllabusUpdateRequest(BaseModel):
    books: List[ExtractedBookRecord] = Field(..., description="Updated list of extracted books.")


class SubjectBooksGroup(BaseModel):
    subject_name: str
    subject_code: Optional[str] = None
    textbooks: List[ExtractedBookRecord] = Field(default_factory=list)
    reference_books: List[ExtractedBookRecord] = Field(default_factory=list)
    suggested_readings: List[ExtractedBookRecord] = Field(default_factory=list)
    total_books: int = 0


class SyllabusSubjectsResponse(BaseModel):
    syllabus_id: str
    university: Optional[str] = None
    department: Optional[str] = None
    programme: Optional[str] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    subjects: List[SubjectBooksGroup] = Field(default_factory=list)
    total_subjects: int = 0


class BatchBookItem(BaseModel):
    id: str = Field(..., description="Item ID within the batch.")
    batch_id: str = Field(..., description="Parent batch ID.")
    extracted_book_id: str = Field(..., description="ID of source extracted book.")
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    subject: Optional[str] = None
    status: str = Field(default="PENDING", description="PENDING, SEARCHING, COMPLETED, NO_RESULTS, FAILED.")
    results_count: int = Field(default=0)
    top_candidate: Optional[BookCandidate] = Field(default=None)
    access_classification: str = Field(default="UNVERIFIED", description="FULL_TEXT, DOWNLOADABLE, PREVIEW, BORROW, NOT_ELIGIBLE, NO_RESULTS, ERROR.")
    provider_statuses: List[ProviderStatus] = Field(default_factory=list)
    error_message: Optional[str] = None
    is_downloaded: bool = Field(default=False, description="Whether an authorized file was acquired and saved to local library.")
    download_job_id: Optional[str] = None
    download_format: Optional[str] = None
    download_path: Optional[str] = None
    download_size_bytes: Optional[int] = None
    download_hash: Optional[str] = None
    updated_at: str


class SearchBatchCreateRequest(BaseModel):
    book_ids: Optional[List[str]] = Field(default=None, description="Specific extracted book IDs to search. If omitted, all selected books are searched.")


class BatchSearchStatusResponse(BaseModel):
    batch_id: str
    syllabus_id: Optional[str] = None
    total_books: int
    completed_books: int
    failed_books: int
    acquired_books: int = Field(default=0, description="Count of successfully acquired/downloaded books in this batch.")
    progress_percentage: float
    status: str = Field(..., description="PENDING, RUNNING, COMPLETED, CANCELLED, FAILED.")
    books: List[BatchBookItem] = Field(default_factory=list)
    created_at: str
    updated_at: str


class AlternativeCategory(str, Enum):
    EXACT_OPEN_ACCESS = "EXACT_OPEN_ACCESS"
    OPEN_TEXTBOOK_ALTERNATIVE = "OPEN_TEXTBOOK_ALTERNATIVE"
    SUPPLEMENTARY_READING = "SUPPLEMENTARY_READING"
    LIBRARY_BORROWING = "LIBRARY_BORROWING"


class AlternativeBookCandidate(BaseModel):
    candidate: BookCandidate
    category: AlternativeCategory
    relevance_explanation: str
    subject_match: bool = True


class AlternativeBookResponse(BaseModel):
    original_candidate_id: str
    original_title: str
    original_licensing_status: LicenseStatus
    alternatives: List[AlternativeBookCandidate] = Field(default_factory=list)
    message: str


class AcquisitionHistoryItem(BaseModel):
    id: str
    record_type: str = Field(..., description="'SEARCH', 'APPROVAL', or 'DOWNLOAD'")
    title: str
    author: Optional[str] = None
    source: str
    status: str
    timestamp: str
    details: Dict[str, Any] = Field(default_factory=dict)
    file_hash: Optional[str] = None


class AcquisitionHistoryResponse(BaseModel):
    total_records: int
    records: List[AcquisitionHistoryItem] = Field(default_factory=list)


class DownloadLibraryItem(BaseModel):
    id: str = Field(..., description="Unique download or provenance record ID.")
    job_id: str
    candidate_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    edition: Optional[str] = None
    publisher: Optional[str] = None
    subject: Optional[str] = None
    syllabus_name: Optional[str] = None
    semester: Optional[str] = None
    provider: str
    format: str = "PDF"
    file_path: str
    file_size_bytes: int = 0
    file_hash: str
    status: str = "VERIFIED"
    downloaded_at: str


class DownloadLibraryResponse(BaseModel):
    total_items: int = 0
    items: List[DownloadLibraryItem] = Field(default_factory=list)


