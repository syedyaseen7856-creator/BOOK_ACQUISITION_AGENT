import {
  BookCandidate,
  BookSearchQuery,
  SearchResponse,
  ApprovalRecord,
  DownloadJob,
  CandidateApprovalRequest,
  SyllabusUploadResponse,
  ExtractedBookRecord,
  BatchSearchStatusResponse,
  AlternativeBookResponse,
  AcquisitionHistoryResponse,
  SyllabusSubjectsResponse,
  DownloadLibraryResponse,
} from '@/types/book';

const API_BASE = '/api';

export async function searchBooks(query: BookSearchQuery): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(query),
  });

  if (!res.ok) {
    let errorMsg = `Search failed with status ${res.status}`;
    try {
      const errData = await res.json();
      if (errData?.detail) errorMsg = errData.detail;
    } catch {
      // fallback
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function getCandidate(candidateId: string): Promise<BookCandidate> {
  const res = await fetch(`${API_BASE}/candidates/${encodeURIComponent(candidateId)}`);
  if (!res.ok) {
    throw new Error(`Failed to load candidate details: HTTP ${res.status}`);
  }
  return res.json();
}

export async function approveCandidate(
  candidateId: string,
  userAffirmation: boolean,
  userNote?: string
): Promise<ApprovalRecord> {
  const payload: CandidateApprovalRequest = {
    user_affirmation: userAffirmation,
    user_note: userNote,
  };

  const res = await fetch(`${API_BASE}/candidates/${encodeURIComponent(candidateId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorMsg = `Approval failed: HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function triggerDownload(
  candidateId: string,
  approvalId?: string,
  simulateOnly: boolean = false
): Promise<DownloadJob> {
  const payload = {
    approval_id: approvalId,
    simulate_only: simulateOnly,
  };

  const res = await fetch(`${API_BASE}/candidates/${encodeURIComponent(candidateId)}/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorMsg = `Download initiation failed: HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function getJob(jobId: string): Promise<DownloadJob> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve job status: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getApprovals(): Promise<ApprovalRecord[]> {
  const res = await fetch(`${API_BASE}/approvals`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve approvals: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getHealth(): Promise<{ status: string; app_name: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Backend health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

// ==========================================
// Syllabus & Batch API Calls
// ==========================================

export async function uploadSyllabusFile(file: File): Promise<SyllabusUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/syllabus/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorMsg = `Upload failed with status ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function parseSyllabusRawText(
  text: string,
  filename: string = 'pasted_syllabus.txt',
  courseTitle?: string
): Promise<SyllabusUploadResponse> {
  const res = await fetch(`${API_BASE}/syllabus/parse-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      filename,
      course_title: courseTitle,
    }),
  });

  if (!res.ok) {
    let errorMsg = `Parsing failed with status ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function getSyllabus(syllabusId: string): Promise<SyllabusUploadResponse> {
  const res = await fetch(`${API_BASE}/syllabus/${encodeURIComponent(syllabusId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch syllabus: HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateSyllabusBooks(syllabusId: string, books: ExtractedBookRecord[]): Promise<ExtractedBookRecord[]> {
  const res = await fetch(`${API_BASE}/syllabus/${encodeURIComponent(syllabusId)}/books`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ books }),
  });

  if (!res.ok) {
    throw new Error(`Failed to update books: HTTP ${res.status}`);
  }
  return res.json();
}

export async function addSyllabusBook(syllabusId: string, book: Partial<ExtractedBookRecord>): Promise<ExtractedBookRecord> {
  const res = await fetch(`${API_BASE}/syllabus/${encodeURIComponent(syllabusId)}/books`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(book),
  });

  if (!res.ok) {
    throw new Error(`Failed to add book: HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteSyllabusBook(syllabusId: string, bookId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/syllabus/${encodeURIComponent(syllabusId)}/books/${encodeURIComponent(bookId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete book: HTTP ${res.status}`);
  }
}

export async function startBatchSearch(syllabusId: string, bookIds?: string[]): Promise<BatchSearchStatusResponse> {
  const res = await fetch(`${API_BASE}/syllabus/${encodeURIComponent(syllabusId)}/search-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_ids: bookIds }),
  });

  if (!res.ok) {
    let msg = `Batch search failed: HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err?.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export async function getBatchStatus(batchId: string, filter?: string): Promise<BatchSearchStatusResponse> {
  const url = filter && filter !== 'ALL'
    ? `${API_BASE}/batches/${encodeURIComponent(batchId)}?filter=${encodeURIComponent(filter)}`
    : `${API_BASE}/batches/${encodeURIComponent(batchId)}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch batch status: HTTP ${res.status}`);
  }
  return res.json();
}

export async function cancelBatch(batchId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/batches/${encodeURIComponent(batchId)}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to cancel batch: HTTP ${res.status}`);
  }
}

export async function retryBatch(batchId: string): Promise<BatchSearchStatusResponse> {
  const res = await fetch(`${API_BASE}/batches/${encodeURIComponent(batchId)}/retry`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to retry batch: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getAlternativeBooks(candidateId: string): Promise<AlternativeBookResponse> {
  const res = await fetch(`${API_BASE}/candidates/${encodeURIComponent(candidateId)}/alternative`);
  if (!res.ok) {
    throw new Error(`Failed to fetch alternatives: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getAcquisitionHistory(recordType?: string, status?: string): Promise<AcquisitionHistoryResponse> {
  const params = new URLSearchParams();
  if (recordType) params.append('record_type', recordType);
  if (status) params.append('status', status);

  const res = await fetch(`${API_BASE}/history?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to load acquisition history: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getProvidersStatus(): Promise<{ providers: Array<{ name: string; status: string; type: string }> }> {
  const res = await fetch(`${API_BASE}/providers/status`);
  if (!res.ok) {
    throw new Error(`Failed to load provider status: HTTP ${res.status}`);
  }
  return res.json();
}

export interface SystemStatusInfo {
  app_name: string;
  version: string;
  environment: string;
  database_connected: boolean;
  gemini_flash_configured: boolean;
  gemini_model: string;
  allowed_domains: string[];
  max_file_size_mb: number;
  approval_expiry_hours: number;
  total_searches_recorded: number;
  total_approvals_recorded: number;
  total_downloads_recorded: number;
}

export async function getSystemStatus(): Promise<SystemStatusInfo> {
  const res = await fetch(`${API_BASE}/system-status`);
  if (!res.ok) {
    throw new Error(`Failed to load system status: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getSyllabusSubjects(syllabusId: string): Promise<SyllabusSubjectsResponse> {
  const res = await fetch(`${API_BASE}/syllabus/${encodeURIComponent(syllabusId)}/subjects`);
  if (!res.ok) {
    throw new Error(`Failed to load syllabus subjects: HTTP ${res.status}`);
  }
  return res.json();
}

export async function getDownloadLibrary(): Promise<DownloadLibraryResponse> {
  const res = await fetch(`${API_BASE}/downloads/library`);
  if (!res.ok) {
    throw new Error(`Failed to load download library: HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteDownloadLibraryItem(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/downloads/library/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete download library item: HTTP ${res.status}`);
  }
}



