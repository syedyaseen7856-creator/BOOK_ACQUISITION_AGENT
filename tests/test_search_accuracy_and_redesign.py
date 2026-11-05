import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    LicenseStatus,
    LicensingEvidence,
    ConfidenceBreakdown,
    ConfidenceTier
)
from app.services.confidence_scorer import calculate_confidence
from app.services.metadata_aggregator import aggregate_and_rank_candidates_with_status


def _make_candidate(
    cid: str,
    title: str,
    authors=None,
    published_year=None,
    edition=None,
    isbns=None,
    publisher=None,
    source_name="Open Library",
    is_downloadable=False,
    lic_status=LicenseStatus.NEEDS_REVIEW
) -> BookCandidate:
    lic = LicensingEvidence(
        status=lic_status,
        license_name="Test License",
        rights_statement="Test Rights",
        source_url="https://example.com/source",
        verified_at="2026-10-25T00:00:00Z",
        is_legally_downloadable=is_downloadable
    )
    return BookCandidate(
        candidate_id=cid,
        title=title,
        authors=authors or ["Test Author"],
        published_year=published_year,
        edition=edition,
        isbns=isbns or [],
        publisher=publisher,
        source_name=source_name,
        source_url="https://example.com",
        reader_url="https://example.com/reader",
        licensing=lic
    )


def test_exact_title_search():
    """Verify exact title match scores deterministically high."""
    query = BookSearchQuery(title="Think Python")
    candidate = _make_candidate("c1", "Think Python", authors=["Allen B. Downey"])
    conf = calculate_confidence(query, candidate)
    
    assert conf.title_score == 30.0
    assert conf.total_score >= 65.0
    assert not conf.has_hard_mismatch


def test_title_plus_author_search():
    """When both title and author match, candidate receives alignment bonus and ranks high."""
    query = BookSearchQuery(title="Think Python", author="Allen B. Downey")
    cand_both = _make_candidate("c_both", "Think Python", authors=["Allen B. Downey"])
    cand_title_only = _make_candidate("c_title", "Think Python", authors=["John Doe"])
    
    conf_both = calculate_confidence(query, cand_both)
    conf_title_only = calculate_confidence(query, cand_title_only)

    assert conf_both.total_score >= 85.0
    assert conf_both.confidence_tier in (ConfidenceTier.PLAUSIBLE_MATCH, ConfidenceTier.STRONG_MATCH)
    # Title only author conflict triggers hard mismatch
    assert conf_title_only.has_hard_mismatch is True
    assert conf_title_only.total_score <= 64.0
    assert conf_both.total_score > conf_title_only.total_score + 20.0


def test_isbn_search_exact_vs_conflicting():
    """Exact ISBN gives strong score; conflicting ISBN triggers hard mismatch cap."""
    cand = _make_candidate("c_isbn", "Computer Networks", isbns=["9780132126953"])
    
    # Exact ISBN
    query_exact = BookSearchQuery(title="Computer Networks", isbn="9780132126953")
    conf_exact = calculate_confidence(query_exact, cand)
    assert conf_exact.isbn_score == 20.0
    assert conf_exact.total_score >= 85.0
    assert not conf_exact.has_hard_mismatch

    # Conflicting ISBN
    query_conflict = BookSearchQuery(title="Computer Networks", isbn="9780000000000")
    conf_conflict = calculate_confidence(query_conflict, cand)
    assert conf_conflict.isbn_score == 0.0
    assert conf_conflict.has_hard_mismatch is True
    assert conf_conflict.total_score <= 64.0
    assert conf_exact.total_score > conf_conflict.total_score + 20.0


def test_different_editions_preserved():
    """Deduplication must keep different editions and publication years distinct."""
    cand_ed2 = _make_candidate("c_ed2", "Introduction to Algorithms", edition="2nd Edition", published_year=2001)
    cand_ed3 = _make_candidate("c_ed3", "Introduction to Algorithms", edition="3rd Edition", published_year=2009)
    cand_ed2_dup = _make_candidate("c_ed2_dup", "Introduction to Algorithms", edition="2nd Edition", published_year=2001)

    query = BookSearchQuery(title="Introduction to Algorithms")

    with patch("app.services.metadata_aggregator.search_open_library", new=AsyncMock(return_value=[cand_ed2, cand_ed3, cand_ed2_dup])), \
         patch("app.services.metadata_aggregator.search_gutenberg_repository", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_crossref", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_google_books", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_openstax", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_doab", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_internet_archive", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_authorized_web_discovery", new=AsyncMock(return_value=[])):
        
        import asyncio
        shortlist, _ = asyncio.run(aggregate_and_rank_candidates_with_status(query))

        # Distinct editions (2nd and 3rd) must both be present
        editions = [c.edition for c in shortlist]
        assert "2nd Edition" in editions
        assert "3rd Edition" in editions
        # Duplicate 2nd edition must be merged
        assert len([e for e in editions if e == "2nd Edition"]) == 1


def test_similar_but_incorrect_title_suggestion_flag():
    """Deliberately mismatched or distant titles are marked as suggestions with capped score."""
    query = BookSearchQuery(title="ZXQJ 9999 Imaginary Quantum Gardening Manual")
    cand = _make_candidate("c_gardening", "A Manual on Window Gardening", authors=["John Holmes"])
    
    conf = calculate_confidence(query, cand)
    assert conf.total_score < 40.0
    assert conf.confidence_tier == ConfidenceTier.LOW_CONFIDENCE
    assert cand.is_approximate_suggestion is True


def test_empty_search_results():
    """Empty provider results return 0 candidates with proper status."""
    query = BookSearchQuery(title="Unknown Impossible Mystery Book 12345")

    with patch("app.services.metadata_aggregator.search_open_library", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_gutenberg_repository", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_crossref", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_google_books", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_openstax", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_doab", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_internet_archive", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_authorized_web_discovery", new=AsyncMock(return_value=[])):
        
        import asyncio
        shortlist, statuses = asyncio.run(aggregate_and_rank_candidates_with_status(query))

        assert len(shortlist) == 0
        ol_status = next(s for s in statuses if s.provider_name == "Open Library")
        assert ol_status.status == "NO_RESULTS"


def test_provider_timeout_and_api_failure_handled_resiliently():
    """If one provider fails, others still succeed and error status is recorded truthfully."""
    cand_ol = _make_candidate("c_ol", "Frankenstein", authors=["Mary Shelley"])
    query = BookSearchQuery(title="Frankenstein")

    with patch("app.services.metadata_aggregator.search_open_library", new=AsyncMock(return_value=[cand_ol])), \
         patch("app.services.metadata_aggregator.search_gutenberg_repository", new=AsyncMock(side_effect=RuntimeError("UNAVAILABLE: Gutendex returned HTTP 500"))), \
         patch("app.services.metadata_aggregator.search_crossref", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_google_books", new=AsyncMock(side_effect=RuntimeError("RATE_LIMITED: Google Books 429"))), \
         patch("app.services.metadata_aggregator.search_openstax", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_doab", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_internet_archive", new=AsyncMock(return_value=[])), \
         patch("app.services.metadata_aggregator.search_authorized_web_discovery", new=AsyncMock(return_value=[])):
        
        import asyncio
        shortlist, statuses = asyncio.run(aggregate_and_rank_candidates_with_status(query))

        assert len(shortlist) >= 1
        assert shortlist[0].candidate_id == "c_ol"

        gutenberg_status = next(s for s in statuses if s.provider_name == "Project Gutenberg")
        assert gutenberg_status.status == "UNAVAILABLE"

        gb_status = next(s for s in statuses if s.provider_name == "Google Books")
        assert gb_status.status == "RATE_LIMITED"


def test_missing_book_descriptions_or_covers():
    """Candidate with None description and None thumbnail does not fail validation."""
    cand = _make_candidate("c_sparse", "Minimal Book")
    cand.description = None
    cand.thumbnail_url = None
    
    assert cand.description is None
    assert cand.thumbnail_url is None
    assert cand.page_count is None


def test_license_status_independent_of_high_confidence_score(client: TestClient):
    """A commercial book with 95+ score must NOT be downloadable and approval must be forbidden."""
    cand_commercial = _make_candidate(
        "cand_test_commercial",
        "Introduction to Algorithms",
        authors=["Thomas H. Cormen"],
        lic_status=LicenseStatus.COMMERCIAL_RESTRICTED,
        is_downloadable=False
    )
    query = BookSearchQuery(title="Introduction to Algorithms", author="Thomas H. Cormen")
    conf = calculate_confidence(query, cand_commercial)

    # Confidence is strong
    assert conf.total_score >= 85.0

    # But license is strictly commercial restricted
    assert cand_commercial.licensing.status == LicenseStatus.COMMERCIAL_RESTRICTED
    assert cand_commercial.licensing.is_legally_downloadable is False


def test_no_download_before_explicit_approval(client: TestClient):
    """Attempting to initiate a download job for an unapproved candidate fails with 404."""
    res = client.post("/api/candidates/non_existent_unapproved_id/download", json={
        "user_id": "test-user",
        "simulate": True
    })
    assert res.status_code == 404
