import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from fastapi import HTTPException
from app.config import settings
from app.db.repository import repository
from app.schemas import (
    BookCandidate,
    ApprovalRecord,
    CandidateApprovalRequest,
    LicenseStatus
)

logger = logging.getLogger(__name__)


def compute_snapshot_hash(candidate: BookCandidate) -> str:
    """Compute a deterministic SHA-256 digest over the critical candidate fields."""
    components = [
        candidate.candidate_id,
        candidate.source_url,
        candidate.licensing.status.value,
        candidate.download_url or "NO_DL",
        candidate.title,
        ",".join(candidate.authors)
    ]
    payload = "|".join(components).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ApprovalService:
    """
    Manages server-side explicit approvals with expiry, snapshot hashing,
    and strict licensing eligibility enforcement.
    """

    def approve_candidate(
        self,
        candidate: BookCandidate,
        request: CandidateApprovalRequest
    ) -> ApprovalRecord:
        """
        Record explicit user approval for an eligible candidate.
        Enforces server-side safeguards:
          1. Mandatory explicit user affirmation.
          2. Mandatory licensing eligibility (MUST be VERIFIED_FOR_PERMITTED_DOWNLOAD).
          3. Generates tamper-detection snapshot hash.
          4. Assigns server-side expiration.
        """
        if not request.user_affirmation:
            raise HTTPException(
                status_code=400,
                detail="Approval rejected: Explicit user affirmation is required to authorize acquisition."
            )

        # Safeguard: Candidate must be verified for permitted download
        if candidate.licensing.status != LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Acquisition prohibited: Candidate '{candidate.title}' has licensing status "
                    f"'{candidate.licensing.status.value}'. Mandatory safeguard: Only candidates "
                    f"with status 'VERIFIED_FOR_PERMITTED_DOWNLOAD' may be approved. "
                    f"User approval cannot bypass legal copyright restrictions."
                )
            )

        if not candidate.licensing.is_legally_downloadable:
            raise HTTPException(
                status_code=403,
                detail="Acquisition prohibited: Licensing flags indicate file is not legally downloadable."
            )

        # Generate Approval ID and Expiry
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.APPROVAL_EXPIRY_HOURS)

        snapshot_hash = compute_snapshot_hash(candidate)

        record = ApprovalRecord(
            approval_id=approval_id,
            candidate_id=candidate.candidate_id,
            source_url=candidate.source_url,
            snapshot_hash=snapshot_hash,
            book_title=candidate.title,
            book_authors=candidate.authors,
            licensing_status=candidate.licensing.status,
            is_legally_downloadable=candidate.licensing.is_legally_downloadable,
            approved_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            is_expired=False,
            user_note=request.user_note,
            is_active=True
        )

        repository.save_approval(record)
        logger.info(f"Recorded server-side approval {approval_id} for candidate {candidate.candidate_id}")
        return record

    def validate_approval_for_download(
        self,
        candidate: BookCandidate,
        approval_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ApprovalRecord]]:
        """
        Validate that a candidate has an active, valid, non-expired approval
        matching its exact current source URL and metadata snapshot.
        """
        record: Optional[ApprovalRecord] = None
        if approval_id:
            record = repository.get_approval(approval_id)
        else:
            record = repository.get_active_approval_for_candidate(candidate.candidate_id)

        if not record:
            return False, f"No approval record found for candidate '{candidate.candidate_id}'. Explicit prior approval required.", None

        if record.candidate_id != candidate.candidate_id:
            return False, f"Approval ID '{record.approval_id}' was issued for a different candidate ({record.candidate_id}).", None

        if record.is_expired:
            return False, f"Approval '{record.approval_id}' has expired (expired at {record.expires_at}). Re-approval required.", record

        if not record.is_active:
            return False, f"Approval '{record.approval_id}' is no longer active.", record

        # Verify source URL match
        if record.source_url != candidate.source_url:
            return False, f"Candidate source URL changed from '{record.source_url}' to '{candidate.source_url}'. Renewed approval required.", record

        # Verify snapshot hash (detects tampering or changed metadata)
        current_hash = compute_snapshot_hash(candidate)
        if record.snapshot_hash != current_hash:
            return False, "Candidate metadata or licensing details have changed since approval. Renewed approval required.", record

        # Re-verify legal licensing
        if record.licensing_status != LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD or not record.is_legally_downloadable:
            return False, "Candidate licensing is not verified for permitted download.", record

        return True, "Approval is valid and authorized for download.", record

    def _enrich_approval_record(self, record: Optional[ApprovalRecord]) -> Optional[ApprovalRecord]:
        if not record:
            return None
        job = repository.get_job_by_approval_id(record.approval_id)
        if job:
            record.download_status = job.status.value
            record.file_hash = job.file_hash
            record.file_size_bytes = job.file_size_bytes

        cand = repository.get_candidate(record.candidate_id)
        if cand and cand.licensing and cand.licensing.evidence_details:
            record.evidence_details = cand.licensing.evidence_details
        return record

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        rec = repository.get_approval(approval_id)
        return self._enrich_approval_record(rec)

    def list_approvals(self) -> List[ApprovalRecord]:
        records = repository.list_approvals()
        return [self._enrich_approval_record(r) for r in records if r]


approval_service = ApprovalService()
