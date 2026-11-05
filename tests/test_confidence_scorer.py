import pytest
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    LicenseStatus,
    LicensingEvidence,
    ConfidenceTier
)
from app.services.confidence_scorer import calculate_confidence


def create_candidate(
    title: str,
    authors: list[str],
    published_year: int = 2020,
    isbns: list[str] = None,
    publisher: str = "MIT Press",
    edition: str = "3rd Edition"
) -> BookCandidate:
    return BookCandidate(
        candidate_id="cand_test_scoring",
        title=title,
        authors=authors,
        publisher=publisher,
        published_year=published_year,
        edition=edition,
        isbns=isbns or [],
        page_count=450,
        source_name="Test Repository",
        source_url="https://example.com/book",
        licensing=LicensingEvidence(
            status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
            license_name="Open Access",
            rights_statement="CC-BY-NC 4.0",
            source_url="https://example.com/book",
            verified_at="2026-10-23T00:00:00Z",
            is_legally_downloadable=True
        )
    )


def test_exact_match_yields_strong_match_tier():
    query = BookSearchQuery(
        title="Frankenstein; Or, The Modern Prometheus",
        author="Mary Wollstonecraft Shelley",
        isbn="9780141439471",
        year=1818,
        edition="Original 1818"
    )
    candidate = create_candidate(
        title="Frankenstein; Or, The Modern Prometheus",
        authors=["Mary Wollstonecraft Shelley"],
        published_year=1818,
        isbns=["9780141439471"],
        publisher="Lackington",
        edition="Original 1818"
    )

    conf = calculate_confidence(query, candidate)

    assert conf.total_score >= 90.0
    assert conf.confidence_tier == ConfidenceTier.STRONG_MATCH
    assert conf.title_score == 30.0
    assert conf.author_score == 25.0
    assert conf.isbn_score == 20.0
    assert conf.edition_year_score == 15.0
    assert conf.publisher_score >= 8.0
    assert conf.has_hard_mismatch is False
    assert len(conf.evidence_used) >= 4


def test_plausible_match_with_minor_variations():
    query = BookSearchQuery(
        title="Operating Systems",
        author="Arpaci-Dusseau",
        year=2018
    )
    candidate = create_candidate(
        title="Operating Systems: Three Easy Pieces",
        authors=["Remzi H. Arpaci-Dusseau", "Andrea C. Arpaci-Dusseau"],
        published_year=2018,
        isbns=["9781985086593"],
        publisher="Arpaci-Dusseau Books",
        edition="Version 1.10"
    )

    conf = calculate_confidence(query, candidate)

    assert 75.0 <= conf.total_score <= 89.9
    assert conf.confidence_tier == ConfidenceTier.PLAUSIBLE_MATCH
    assert conf.has_hard_mismatch is False


def test_hard_mismatch_conflicting_isbn_caps_score():
    """A conflicting ISBN must never be hidden by high title similarity."""
    query = BookSearchQuery(
        title="Artificial Intelligence: A Modern Approach",
        author="Stuart Russell",
        isbn="9780134610993"  # 4th Edition ISBN
    )
    candidate = create_candidate(
        title="Artificial Intelligence: A Modern Approach",
        authors=["Stuart Russell", "Peter Norvig"],
        published_year=2003,
        isbns=["9780137903955"],  # Conflicting 2nd Edition ISBN
        publisher="Prentice Hall"
    )

    conf = calculate_confidence(query, candidate)

    assert conf.has_hard_mismatch is True
    assert conf.total_score <= 64.0  # Must be capped below 75 into LOW_CONFIDENCE
    assert conf.confidence_tier == ConfidenceTier.LOW_CONFIDENCE
    assert any("Conflicting ISBN" in m for m in conf.mismatches_and_uncertainty)
    assert any("HARD MISMATCH TRIGGERED" in e for e in conf.explanation)


def test_hard_mismatch_conflicting_author():
    """Conflicting author must trigger hard mismatch safeguard."""
    query = BookSearchQuery(
        title="Principles of Compiler Design",
        author="Alfred Aho"
    )
    candidate = create_candidate(
        title="Principles of Compiler Design",
        authors=["John Smith", "Robert Davis"],  # Completely different authors
        published_year=2015
    )

    conf = calculate_confidence(query, candidate)

    assert conf.has_hard_mismatch is True
    assert conf.total_score <= 64.0
    assert conf.confidence_tier == ConfidenceTier.LOW_CONFIDENCE
    assert any("Author conflict" in m for m in conf.mismatches_and_uncertainty)


def test_missing_query_fields_documented():
    query = BookSearchQuery(title="Calculus")
    candidate = create_candidate(
        title="Calculus",
        authors=["James Stewart"],
        published_year=2015
    )

    conf = calculate_confidence(query, candidate)

    assert "Query author missing" in conf.missing_fields
    assert "Query ISBN missing" in conf.missing_fields
