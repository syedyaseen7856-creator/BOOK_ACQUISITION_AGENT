"""Backward-compatibility bridge re-exporting from app.schemas."""
from app.schemas import (
    LicenseStatus,
    LicensingEvidence,
    ConfidenceBreakdown,
    ConfidenceTier,
    BookSearchQuery,
    BookCandidate,
    CandidateApprovalRequest,
    ApprovalRecord,
    DownloadJob,
    DownloadJobStatus,
    SystemStatus,
    SearchResponse,
    ProviderStatus,
)

__all__ = [
    "LicenseStatus",
    "LicensingEvidence",
    "ConfidenceBreakdown",
    "ConfidenceTier",
    "BookSearchQuery",
    "BookCandidate",
    "CandidateApprovalRequest",
    "ApprovalRecord",
    "DownloadJob",
    "DownloadJobStatus",
    "SystemStatus",
    "SearchResponse",
    "ProviderStatus",
]
