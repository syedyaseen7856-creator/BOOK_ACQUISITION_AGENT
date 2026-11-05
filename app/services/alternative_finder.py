import logging
from typing import List, Optional
from app.schemas import (
    BookCandidate,
    BookSearchQuery,
    AlternativeBookResponse,
    AlternativeBookCandidate,
    AlternativeCategory,
    LicenseStatus
)
from app.services.open_access_repos import search_openstax, search_doab
from app.services.authorized_repos import search_gutenberg_repository
from app.services.open_library import search_open_library
from app.services.confidence_scorer import calculate_confidence

logger = logging.getLogger(__name__)


class AlternativeFinder:
    """
    Discovers legitimate open-access, public domain, or borrowable alternatives
    when a reference book is commercial, in-copyright, or restricted behind paywalls.
    """

    async def find_alternatives(self, candidate: BookCandidate) -> AlternativeBookResponse:
        """
        Search for legitimate open alternatives matching the book's subject or title.
        """
        alternatives: List[AlternativeBookCandidate] = []

        # Derive query keywords from candidate title and categories
        query_subject = candidate.categories[0] if candidate.categories else ""
        clean_title = candidate.title

        # 1. Search OpenStax Open Educational Textbooks
        ostax_query = BookSearchQuery(
            title=clean_title,
            subject=query_subject or clean_title,
            q=clean_title
        )
        try:
            ostax_cands = await search_openstax(ostax_query, limit=3)
            for c in ostax_cands:
                cat = AlternativeCategory.EXACT_OPEN_ACCESS if c.title.lower() == clean_title.lower() else AlternativeCategory.OPEN_TEXTBOOK_ALTERNATIVE
                c.confidence = calculate_confidence(ostax_query, c)
                alternatives.append(
                    AlternativeBookCandidate(
                        candidate=c,
                        category=cat,
                        relevance_explanation=f"Peer-reviewed OpenStax open textbook covering {c.categories[0] if c.categories else 'the discipline'} with complete CC-BY full-text reading and PDF download.",
                        subject_match=True
                    )
                )
        except Exception as e:
            logger.debug(f"OpenStax alternative search error: {e}")

        # 2. Search Gutenberg for public domain classics / foundational references
        gut_query = BookSearchQuery(
            title=clean_title,
            author=candidate.authors[0] if candidate.authors else None
        )
        try:
            gut_cands = await search_gutenberg_repository(gut_query, limit=2)
            for c in gut_cands:
                cat = AlternativeCategory.EXACT_OPEN_ACCESS if c.title.lower() == clean_title.lower() else AlternativeCategory.SUPPLEMENTARY_READING
                c.confidence = calculate_confidence(gut_query, c)
                alternatives.append(
                    AlternativeBookCandidate(
                        candidate=c,
                        category=cat,
                        relevance_explanation="Public domain edition available on Project Gutenberg with authorized full-text access.",
                        subject_match=True
                    )
                )
        except Exception as e:
            logger.debug(f"Gutenberg alternative search error: {e}")

        # 3. Search Open Library for Controlled Digital Lending (Borrowing)
        ol_query = BookSearchQuery(
            title=clean_title,
            author=candidate.authors[0] if candidate.authors else None
        )
        try:
            ol_cands = await search_open_library(ol_query, limit=2)
            for c in ol_cands:
                if c.source_url != candidate.source_url:
                    c.confidence = calculate_confidence(ol_query, c)
                    alternatives.append(
                        AlternativeBookCandidate(
                            candidate=c,
                            category=AlternativeCategory.LIBRARY_BORROWING,
                            relevance_explanation="Available to borrow legitimately through Open Library / Internet Archive digital library loans.",
                            subject_match=True
                        )
                    )
        except Exception as e:
            logger.debug(f"Open Library alternative search error: {e}")

        msg = (
            f"Found {len(alternatives)} legitimate open alternative(s) for '{candidate.title}'."
            if alternatives
            else f"No immediate open-access alternative found for '{candidate.title}'."
        )

        return AlternativeBookResponse(
            original_candidate_id=candidate.candidate_id,
            original_title=candidate.title,
            original_licensing_status=candidate.licensing.status,
            alternatives=alternatives,
            message=msg
        )


alternative_finder = AlternativeFinder()
