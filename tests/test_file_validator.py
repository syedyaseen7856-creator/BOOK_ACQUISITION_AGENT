import tempfile
from pathlib import Path
import pypdf
from app.services.file_validator import (
    validate_pdf_file,
    compute_file_sha256,
    quarantine_file
)
from app.config import settings


def test_valid_pdf_validation():
    # Create a small valid PDF using pypdf
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(tmp)
        tmp_path = Path(tmp.name)

    try:
        is_valid, msg, meta = validate_pdf_file(tmp_path)
        assert is_valid is True
        assert "succeeded" in msg
        assert meta["page_count"] == 1
        assert meta["is_encrypted"] is False
        assert len(meta["file_hash"]) == 64  # Valid SHA-256 hex string
    finally:
        tmp_path.unlink(missing_ok=True)


def test_invalid_header_fails_and_quarantines():
    # Create a fake file with invalid content
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"NOT A REAL PDF FILE HEADER")
        tmp_path = Path(tmp.name)

    try:
        is_valid, msg, _ = validate_pdf_file(tmp_path)
        assert is_valid is False
        assert "header does not contain '%PDF-'" in msg

        # Test quarantine
        q_path = quarantine_file(tmp_path, reason="Invalid signature")
        assert q_path.exists()
        assert q_path.parent == settings.quarantine_path
        q_path.unlink(missing_ok=True)
        q_path.with_suffix(".quarantine.txt").unlink(missing_ok=True)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_empty_file_rejected():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        is_valid, msg, _ = validate_pdf_file(tmp_path)
        assert is_valid is False
        assert "0 bytes" in msg
    finally:
        tmp_path.unlink(missing_ok=True)
