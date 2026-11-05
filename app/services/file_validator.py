import hashlib
import logging
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import pypdf
from app.config import settings

logger = logging.getLogger(__name__)


def compute_file_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 hash of a file efficiently via streaming chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_pdf_file(file_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate a downloaded PDF file for:
      - Valid file signature (%PDF-)
      - Minimum readable structure & readability
      - Valid page count (page_count >= 1)
      - Encryption / password protection status
      - SHA-256 hash
    Returns (is_valid, message, metadata_dict)
    """
    if not file_path.exists():
        return False, "File does not exist.", {}

    file_size = file_path.stat().st_size
    if file_size == 0:
        return False, "Downloaded file is empty (0 bytes).", {}

    # 1. File signature check
    try:
        with open(file_path, "rb") as f:
            header = f.read(1024)
            if b"%PDF-" not in header:
                return False, "Invalid file signature: header does not contain '%PDF-'.", {}
    except Exception as e:
        return False, f"Failed to inspect file header: {e}", {}

    # 2. SHA-256 calculation
    file_hash = compute_file_sha256(file_path)

    # 3. Readability & page count check using pypdf
    try:
        reader = pypdf.PdfReader(str(file_path))

        if reader.is_encrypted:
            return False, "PDF is password-protected or encrypted; unable to index.", {
                "file_hash": file_hash,
                "file_size_bytes": file_size,
                "is_encrypted": True
            }

        page_count = len(reader.pages)
        if page_count < 1:
            return False, "PDF contains zero pages.", {
                "file_hash": file_hash,
                "file_size_bytes": file_size,
                "page_count": 0
            }

        # Attempt to read text from the first page to confirm uncorrupted structure
        first_page = reader.pages[0]
        sample_text = first_page.extract_text() or ""

        return True, "PDF validation succeeded.", {
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "page_count": page_count,
            "sample_text_length": len(sample_text),
            "is_encrypted": False
        }


    except Exception as e:
        logger.warning(f"pypdf validation failed for {file_path}: {e}")
        return False, f"Corrupted or invalid PDF structure: {str(e)}", {
            "file_hash": file_hash,
            "file_size_bytes": file_size
        }


def validate_epub_file(file_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate a downloaded EPUB file for:
      - Valid file signature (PK\x03\x04 ZIP header)
      - Valid EPUB packaging (mimetype file or META-INF container)
      - Non-zero size
      - SHA-256 hash
    Returns (is_valid, message, metadata_dict)
    """
    import zipfile

    if not file_path.exists():
        return False, "File does not exist.", {}

    file_size = file_path.stat().st_size
    if file_size == 0:
        return False, "Downloaded file is empty (0 bytes).", {}

    # 1. File signature check (ZIP archive header)
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
            if header != b"PK\x03\x04":
                return False, "Invalid file signature: header does not match ZIP/EPUB format.", {}
    except Exception as e:
        return False, f"Failed to inspect file header: {e}", {}

    file_hash = compute_file_sha256(file_path)

    # 2. Structural packaging check using zipfile
    try:
        with zipfile.ZipFile(file_path) as z:
            names = z.namelist()
            if "mimetype" in names:
                mtype = z.read("mimetype").decode("ascii", errors="ignore").strip()
                if "application/epub+zip" not in mtype:
                    return False, f"Invalid EPUB mimetype: '{mtype}'.", {
                        "file_hash": file_hash,
                        "file_size_bytes": file_size
                    }
            elif not any("meta-inf" in n.lower() or "oebps" in n.lower() for n in names):
                return False, "ZIP archive lacks valid EPUB structure (missing META-INF or OEBPS container).", {
                    "file_hash": file_hash,
                    "file_size_bytes": file_size
                }

        return True, "EPUB validation succeeded.", {
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "format": "EPUB",
            "page_count": None
        }
    except Exception as e:
        logger.warning(f"EPUB validation failed for {file_path}: {e}")
        return False, f"Corrupted or invalid EPUB archive: {str(e)}", {
            "file_hash": file_hash,
            "file_size_bytes": file_size
        }


def quarantine_file(file_path: Path, reason: str) -> Path:
    """
    Move an invalid, corrupted, or suspicious file into data/quarantine/
    with an audit reason note.
    """
    quarantine_dir = settings.quarantine_path
    target_path = quarantine_dir / file_path.name

    # Handle collisions in quarantine
    if target_path.exists():
        target_path = quarantine_dir / f"quarantined_{file_path.stem}_{hashlib.md5(reason.encode()).hexdigest()[:6]}{file_path.suffix}"

    shutil.move(str(file_path), str(target_path))
    logger.warning(f"Quarantined suspicious file: {file_path} -> {target_path} (Reason: {reason})")

    # Write quarantine metadata note
    note_file = target_path.with_suffix(".quarantine.txt")
    with open(note_file, "w", encoding="utf-8") as f:
        f.write(f"Quarantined At: {settings.storage_path}\nReason: {reason}\nOriginal Name: {file_path.name}\n")

    return target_path
