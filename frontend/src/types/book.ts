export type LicenseStatus =
  | 'VERIFIED_FOR_PERMITTED_DOWNLOAD'
  | 'COMMERCIAL_RESTRICTED'
  | 'NEEDS_REVIEW'
  | 'NOT_ELIGIBLE';

export type ConfidenceTier = 'STRONG_MATCH' | 'PLAUSIBLE_MATCH' | 'LOW_CONFIDENCE';

export type AccessType = 'FULL_TEXT' | 'PREVIEW' | 'PUBLISHER_PAGE' | 'UNAVAILABLE';

export type ReaderType =
  | 'FULL_READER'
  | 'EMBEDDED_PDF'
  | 'HTML_READER'
  | 'PREVIEW_ONLY'
  | 'OFFICIAL_PAGE'
  | 'NONE';

export interface LicensingEvidence {
  status: LicenseStatus;
  license_name: string;
  rights_statement: string;
  source_url: string;
  terms_url?: string | null;
  evidence_details: string[];
  verified_at: string;
  intended_use: string;
  is_legally_downloadable: boolean;
}

export interface ConfidenceBreakdown {
  total_score: number;
  title_score: number;
  author_score: number;
  isbn_score: number;
  edition_year_score: number;
  publisher_score: number;
  confidence_tier: ConfidenceTier;
  evidence_used: string[];
  missing_fields: string[];
  mismatches_and_uncertainty: string[];
  explanation: string[];
  has_hard_mismatch: boolean;
}

export interface BookCandidate {
  candidate_id: string;
  title: string;
  alternate_titles: string[];
  subtitle?: string | null;
  authors: string[];
  publisher?: string | null;
  published_date?: string | null;
  published_year?: number | null;
  edition?: string | null;
  isbns: string[];
  isbn_10?: string | null;
  isbn_13?: string | null;
  page_count?: number | null;
  language?: string | null;
  categories: string[];
  description?: string | null;
  thumbnail_url?: string | null;
  source_name: string;
  source_url: string;
  reader_url?: string | null;
  embed_url?: string | null;
  external_search_url?: string | null;
  preview_url?: string | null;
  pdf_url?: string | null;
  epub_url?: string | null;
  access_state?:
    | 'AUTHORIZED_DOWNLOAD'
    | 'FULL_TEXT_ONLINE'
    | 'PREVIEW_ONLY'
    | 'BORROWING_REQUIRED'
    | 'LOGIN_REQUIRED'
    | 'COMMERCIAL_ACCESS'
    | 'RIGHTS_UNCLEAR'
    | 'UNAVAILABLE';
  access_type: AccessType;
  access_message?: string | null;
  reader_type: ReaderType;
  can_embed: boolean;
  download_url?: string | null;
  format?: string | null;
  is_open_access?: boolean;
  confidence?: ConfidenceBreakdown | null;
  licensing: LicensingEvidence;
  missing_or_conflicting_metadata: string[];
  is_approximate_suggestion: boolean;
  is_demo_data: boolean;
  match_type?: 'EXACT_MATCH' | 'ALTERNATE_EDITION' | 'RELATED_PUBLICATION' | 'UNRELATED';
  match_explanation?: string | null;
}

export interface ProviderStatus {
  provider_name: string;
  status: 'SUCCESS' | 'RATE_LIMITED' | 'NO_RESULTS' | 'ERROR' | 'UNAVAILABLE' | 'NOT_CONFIGURED' | 'CIRCUIT_OPEN' | 'CACHED';
  message?: string | null;
  results_count: number;
  elapsed_ms?: number | null;
  cached?: boolean;
  retry_after?: number | null;
}

export interface BookSearchQuery {
  q?: string;
  title?: string;
  author?: string;
  isbn?: string;
  edition?: string;
  year?: number;
  subject?: string;
  use_mock_data?: boolean;
}

export interface SearchResponse {
  query: BookSearchQuery;
  total_candidates: number;
  candidates: BookCandidate[];
  related_publications?: BookCandidate[];
  total_related?: number;
  provider_statuses: ProviderStatus[];
}

export interface CandidateApprovalRequest {
  user_affirmation: boolean;
  user_note?: string;
}

export interface ApprovalRecord {
  approval_id: string;
  candidate_id: string;
  source_url: string;
  snapshot_hash: string;
  book_title: string;
  book_authors: string[];
  licensing_status: LicenseStatus;
  is_legally_downloadable: boolean;
  approved_at: string;
  expires_at: string;
  is_expired: boolean;
  user_note?: string | null;
  is_active: boolean;
  download_status?: string | null;
  file_hash?: string | null;
  file_size_bytes?: number | null;
  evidence_details: string[];
}

export interface DownloadJob {
  job_id: string;
  candidate_id: string;
  approval_id: string;
  status: 'PENDING' | 'DOWNLOADING' | 'VALIDATING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  sha256_hash?: string | null;
  file_size_bytes?: number | null;
  downloaded_file_path?: string | null;
  quarantine_reason?: string | null;
  is_valid_pdf: boolean;
}

// ==========================================
// Syllabus, Batch, Alternative & History Types
// ==========================================

export type BookType = 'TEXTBOOK' | 'REFERENCE' | 'SUGGESTED_READING';

export interface ExtractedBookRecord {
  id: string;
  syllabus_id: string;
  title: string;
  clean_title?: string | null;
  author?: string | null;
  authors?: string[];
  edition?: string | null;
  year?: number | null;
  publisher?: string | null;
  isbn?: string | null;
  book_type: BookType;
  priority_status?: 'REQUIRED' | 'RECOMMENDED' | 'OPTIONAL' | string | null;
  subject?: string | null;
  subject_code?: string | null;
  page_number?: number | null;
  context_snippet?: string | null;
  confidence: number;
  is_selected: boolean;
  created_at?: string | null;
}

export interface SyllabusUploadResponse {
  syllabus_id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  page_count?: number | null;
  university?: string | null;
  department?: string | null;
  programme?: string | null;
  semester?: string | null;
  academic_year?: string | null;
  extracted_subjects: string[];
  books: ExtractedBookRecord[];
  total_extracted: number;
  status: string;
  message?: string | null;
}

export interface SubjectBooksGroup {
  subject_name: string;
  subject_code?: string | null;
  textbooks: ExtractedBookRecord[];
  reference_books: ExtractedBookRecord[];
  suggested_readings: ExtractedBookRecord[];
  total_books: number;
}

export interface SyllabusSubjectsResponse {
  syllabus_id: string;
  university?: string | null;
  department?: string | null;
  programme?: string | null;
  semester?: string | null;
  academic_year?: string | null;
  subjects: SubjectBooksGroup[];
  total_subjects: number;
}

export interface BatchBookItem {
  id: string;
  batch_id: string;
  extracted_book_id: string;
  title: string;
  author?: string | null;
  isbn?: string | null;
  subject?: string | null;
  status: string; // PENDING, SEARCHING, COMPLETED, NO_RESULTS, FAILED
  results_count: number;
  top_candidate?: BookCandidate | null;
  access_classification: string; // FULL_TEXT, DOWNLOADABLE, PREVIEW, BORROW, NOT_ELIGIBLE, NO_RESULTS, ERROR
  provider_statuses: ProviderStatus[];
  error_message?: string | null;
  is_downloaded?: boolean;
  download_job_id?: string | null;
  download_format?: string | null;
  download_path?: string | null;
  download_size_bytes?: number | null;
  download_hash?: string | null;
  updated_at: string;
}

export interface BatchSearchStatusResponse {
  batch_id: string;
  syllabus_id?: string | null;
  total_books: number;
  completed_books: number;
  failed_books: number;
  acquired_books?: number;
  progress_percentage: number;
  status: string; // PENDING, RUNNING, COMPLETED, CANCELLED, FAILED
  books: BatchBookItem[];
  created_at: string;
  updated_at: string;
}

export type AlternativeCategory =
  | 'EXACT_OPEN_ACCESS'
  | 'OPEN_TEXTBOOK_ALTERNATIVE'
  | 'SUPPLEMENTARY_READING'
  | 'LIBRARY_BORROWING';

export interface AlternativeBookCandidate {
  candidate: BookCandidate;
  category: AlternativeCategory;
  relevance_explanation: string;
  subject_match: boolean;
}

export interface AlternativeBookResponse {
  original_candidate_id: string;
  original_title: string;
  original_licensing_status: LicenseStatus;
  alternatives: AlternativeBookCandidate[];
  message: string;
}

export interface AcquisitionHistoryItem {
  id: string;
  record_type: 'SEARCH' | 'APPROVAL' | 'DOWNLOAD';
  title: string;
  author?: string | null;
  source: string;
  status: string;
  timestamp: string;
  details: Record<string, unknown>;
  file_hash?: string | null;
}

export interface AcquisitionHistoryResponse {
  total_records: number;
  records: AcquisitionHistoryItem[];
}

export interface DownloadLibraryItem {
  id: string;
  job_id: string;
  candidate_id: string;
  title: string;
  authors: string[];
  edition?: string | null;
  publisher?: string | null;
  subject?: string | null;
  syllabus_name?: string | null;
  semester?: string | null;
  provider: string;
  format: string;
  file_path: string;
  file_size_bytes: number;
  file_hash: string;
  status: string;
  downloaded_at: string;
}

export interface DownloadLibraryResponse {
  total_items: number;
  items: DownloadLibraryItem[];
}

