import pytest
from app.schemas import LicenseStatus
from app.services.licensing_verifier import verify_licensing


@pytest.mark.asyncio
async def test_gutenberg_source_verified_for_permitted_download():
    lic = await verify_licensing(
        source_name="Project Gutenberg",
        source_url="https://www.gutenberg.org/ebooks/84",
        title="Frankenstein",
        published_year=1818
    )

    assert lic.status == LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD
    assert lic.is_legally_downloadable is True
    assert "gutenberg" in lic.terms_url.lower()
    assert len(lic.evidence_details) >= 2


@pytest.mark.asyncio
async def test_open_access_creative_commons_verified():
    lic = await verify_licensing(
        source_name="Directory of Open Access Books",
        source_url="https://example.com/ostep",
        title="Operating Systems",
        published_year=2018,
        raw_rights="Creative Commons CC-BY-NC 4.0"
    )

    assert lic.status == LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD
    assert lic.is_legally_downloadable is True
    assert "Creative Commons" in lic.license_name


@pytest.mark.asyncio
async def test_pre_1929_year_verified_as_public_domain():
    lic = await verify_licensing(
        source_name="Historical Open Repository",
        source_url="https://example.com/archive",
        title="Ancient World History",
        published_year=1880
    )

    assert lic.status == LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD
    assert lic.is_legally_downloadable is True


@pytest.mark.asyncio
async def test_commercial_google_books_preview_is_not_eligible():
    access_info = {
        "publicDomain": False,
        "viewability": "PARTIAL",
        "accessViewStatus": "SAMPLE"
    }
    lic = await verify_licensing(
        source_name="Google Books",
        source_url="https://books.google.com/books?id=123",
        title="Modern Physics Textbook",
        published_year=2021,
        google_books_access_info=access_info
    )

    assert lic.status == LicenseStatus.NOT_ELIGIBLE
    assert lic.is_legally_downloadable is False
    assert any("commercial copyright" in e.lower() for e in lic.evidence_details)


@pytest.mark.asyncio
async def test_open_library_controlled_digital_lending_is_not_eligible():
    ol_details = {
        "lending_identifier_s": "introtoalgo00corm",
        "ia_collection_s": "inlibrary; printdisabled"
    }
    lic = await verify_licensing(
        source_name="Open Library",
        source_url="https://openlibrary.org/books/OL123M",
        title="Algorithms",
        published_year=2009,
        open_library_details=ol_details
    )

    assert lic.status == LicenseStatus.NOT_ELIGIBLE
    assert lic.is_legally_downloadable is False
    assert any("controlled digital lending" in e.lower() for e in lic.evidence_details)


@pytest.mark.asyncio
async def test_unclear_rights_defaults_to_needs_review():
    lic = await verify_licensing(
        source_name="University Website",
        source_url="https://example.com/item",
        title="Department Pamphlet",
        published_year=1995,
        raw_rights=None
    )

    assert lic.status == LicenseStatus.NEEDS_REVIEW
    assert lic.is_legally_downloadable is False
    assert any("Ambiguous licensing requires manual review" in e for e in lic.evidence_details)
