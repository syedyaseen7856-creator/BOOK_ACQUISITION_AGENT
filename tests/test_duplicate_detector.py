from app.services.duplicate_detector import check_for_duplicate
from app.db.repository import repository


def test_duplicate_detection_lifecycle():
    fake_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Initially not duplicate
    is_dup, record = check_for_duplicate(fake_hash)
    assert is_dup is False
    assert record is None

    # Register provenance
    repository.save_provenance(
        file_hash=fake_hash,
        candidate_id="cand_test_dup",
        job_id="job_test_dup",
        file_path="/tmp/book.pdf",
        provenance={"candidate_id": "cand_test_dup", "title": "Duplicated Book"}
    )

    # Now duplicate should be detected
    is_dup2, record2 = check_for_duplicate(fake_hash)
    assert is_dup2 is True
    assert record2["candidate_id"] == "cand_test_dup"
    assert record2["title"] == "Duplicated Book"
