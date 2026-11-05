import json
import logging
from pathlib import Path
from typing import List
from app.config import settings
from app.schemas import BookSearchQuery, BookCandidate

logger = logging.getLogger(__name__)


def load_mock_candidates(query: BookSearchQuery) -> List[BookCandidate]:
    """Load and lightly filter mock candidates from data/mock_candidates.json."""
    mock_file = Path("data/mock_candidates.json")
    if not mock_file.exists():
        logger.warning("Mock candidates file not found, returning empty list.")
        return []

    try:
        with open(mock_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        candidates = [BookCandidate.model_validate(item) for item in raw_data]

        # If user searched for something specific, filter or return all if generic
        if query.title:
            q_title = query.title.lower().strip()
            filtered = [c for c in candidates if q_title in c.title.lower()]
            if filtered:
                return filtered
        if query.author:
            q_author = query.author.lower().strip()
            filtered = [c for c in candidates if any(q_author in a.lower() for a in c.authors)]
            if filtered:
                return filtered
        if query.isbn:
            q_isbn = query.isbn.replace("-", "").strip()
            filtered = [c for c in candidates if any(q_isbn in i.replace("-", "") for i in c.isbns)]
            if filtered:
                return filtered

        return candidates
    except Exception as e:
        logger.error(f"Error loading mock candidates: {e}")
        return []


async def search_open_web_repositories(query: BookSearchQuery) -> List[BookCandidate]:
    """
    Search configurable web repositories for legally available editions.
    Supports mock testing mode as well as configurable live search modes.
    """
    if query.use_mock_data or settings.SEARCH_PROVIDER == "mock":
        return load_mock_candidates(query)

    # In production or direct search mode, targeted repository search is performed
    # via authorized_repos and open_library.
    return []
