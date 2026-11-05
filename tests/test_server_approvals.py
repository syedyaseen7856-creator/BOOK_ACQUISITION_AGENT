from datetime import datetime, timezone, timedelta
import pytest
from app.schemas import (
    BookCandidate,
    CandidateApprovalRequest,
    LicenseStatus,
    LicensingEvidence,
    ApprovalRecord
)
from app.services.approval_service import approval_service, compute_snapshot_hash
from app.db.repository import repository


def create_test_candidate(candidate_id: str, status: LicenseStatus, is_dl: bool) -> BookCandidate:
    return BookCandidate(
        candidate_id=candidate_id,
        title="Test Book Title",
        authors=["Author One"],
        publisher="Open Press",
        published_year=2021,
        edition="1st",
        isbns=["9781234567890"],
        source_name="Open Repository",
        source_url="https://example.com/books/1",
        download_url="https://example.com/books/1.pdf",
        licensing=LicensingEvidence(
            status=status,
            license_name="Test License",
            rights_statement="Declared Rights",
            source_url="https://example.com/books/1",
            verified_at="2026-10-23T00:00:00Z",
            is_legally_downloadable=is_dl
        )
    )


def test_approve_eligible_candidate_succeeds():
    cand = create_test_candidate("cand_eligible_1", LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD, True)
    req = CandidateApprovalRequest(user_affirmation=True, user_note="Approved for CS Syllabus")

    record = approval_service.approve_candidate(cand, req)

    assert record.candidate_id == cand.candidate_id
    assert record.is_legally_downloadable is True
    assert record.snapshot_hash is not None
    assert record.is_expired is False
    assert record.user_note == "Approved for CS Syllabus"

    # Verify retrieval from SQLite
    saved = repository.get_approval(record.approval_id)
    assert saved is not None
    assert saved.approval_id == record.approval_id


def test_approval_fails_without_user_affirmation():
    cand = create_test_candidate("cand_eligible_2", LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD, True)
    req = CandidateApprovalRequest(user_affirmation=False)

    with pytest.raises(Exception) as excinfo:
        approval_service.approve_candidate(cand, req)
    assert "Explicit user affirmation is required" in str(excinfo.value)


def test_approval_blocks_not_eligible_candidates():
    cand = create_test_candidate("cand_comm_1", LicenseStatus.NOT_ELIGIBLE, False)
    req = CandidateApprovalRequest(user_affirmation=True)

    with pytest.raises(Exception) as excinfo:
        approval_service.approve_candidate(cand, req)
    assert "Acquisition prohibited" in str(excinfo.value)
    assert "VERIFIED_FOR_PERMITTED_DOWNLOAD" in str(excinfo.value)


def test_approval_blocks_needs_review_candidates():
    cand = create_test_candidate("cand_ambig_1", LicenseStatus.NEEDS_REVIEW, False)
    req = CandidateApprovalRequest(user_affirmation=True)

    with pytest.raises(Exception) as excinfo:
        approval_service.approve_candidate(cand, req)
    assert "Acquisition prohibited" in str(excinfo.value)


def test_download_validation_rejects_expired_approval():
    cand = create_test_candidate("cand_exp_1", LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD, True)
    req = CandidateApprovalRequest(user_affirmation=True)
    record = approval_service.approve_candidate(cand, req)

    # Manually expire the approval in SQLite
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    record.expires_at = past_iso
    repository.save_approval(record)

    is_valid, msg, _ = approval_service.validate_approval_for_download(cand, record.approval_id)
    assert is_valid is False
    assert "expired" in msg.lower()


def test_download_validation_detects_changed_source_url():
    cand = create_test_candidate("cand_url_mod", LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD, True)
    req = CandidateApprovalRequest(user_affirmation=True)
    record = approval_service.approve_candidate(cand, req)

    # Candidate source URL changes after approval
    cand.source_url = "https://different-mirror.org/books/1"

    is_valid, msg, _ = approval_service.validate_approval_for_download(cand, record.approval_id)
    assert is_valid is False
    assert "source URL changed" in msg


def test_download_validation_rejects_mismatched_candidate_id():
    cand_a = create_test_candidate("cand_a", LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD, True)
    cand_b = create_test_candidate("cand_b", LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD, True)
    req = CandidateApprovalRequest(user_affirmation=True)
    record_a = approval_service.approve_candidate(cand_a, req)

    # Try validating candidate B using approval for candidate A
    is_valid, msg, _ = approval_service.validate_approval_for_download(cand_b, record_a.approval_id)
    assert is_valid is False
    assert "issued for a different candidate" in msg
