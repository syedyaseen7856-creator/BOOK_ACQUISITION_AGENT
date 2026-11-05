import logging
from typing import Tuple, Optional, Dict, Any
from app.db.repository import repository

logger = logging.getLogger(__name__)


def check_for_duplicate(file_hash: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if a file with this exact SHA-256 hash has already been downloaded
    and recorded in the provenance registry.
    """
    existing = repository.find_provenance_by_hash(file_hash)
    if existing:
        logger.info(f"Duplicate detected for hash {file_hash}: already recorded as candidate {existing.get('candidate_id')}")
        return True, existing
    return False, None
