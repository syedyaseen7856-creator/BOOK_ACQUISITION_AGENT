import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.syllabus_extractor import syllabus_extractor
from app.schemas import BookType, ExtractedBookRecord, BookSearchQuery
from app.services.open_access_repos import search_openstax
from app.db.repository import repository

client = TestClient(app)

SAMPLE_SYLLABUS_TEXT = """
Department of Computer Science and Engineering
Course Name: CS204 - Operating Systems and System Programming
Semester: Fall 2026

Course Objectives:
Understanding the design and implementation of modern computer operating systems.

Unit I: Process Management and Concurrency
Processes, threads, CPU scheduling, synchronization.
Textbook Reference:
1. Silberschatz, A., Galvin, P.B., and Gagne, G., "Operating System Concepts", 10th Edition, Wiley, 2018. ISBN: 978-1119456339.

Unit II: Memory and Storage Architecture
Virtual memory, paging, page replacement algorithms.
Prescribed Books:
2. Arpaci-Dusseau, Remzi H., and Arpaci-Dusseau, Andrea C., "Operating Systems: Three Easy Pieces", 1st Edition, Arpaci-Dusseau Books, 2018.

Unit III: Distributed Systems & Security
Case studies in modern distributed OS design.
Reference Books:
3. Andrew S. Tanenbaum and Herbert Bos, "Modern Operating Systems", 4th Edition, Pearson, 2014. ISBN: 978-0133591620.
4. "The Design of the UNIX Operating System" by Maurice J. Bach, Prentice Hall, 1986.
"""


def test_syllabus_extractor_parsing():
    """Verify text syllabus parsing extracts subjects, citations, and metadata."""
    content = SAMPLE_SYLLABUS_TEXT.encode("utf-8")
    subjects, books, page_count = syllabus_extractor.parse_syllabus(
        content=content,
        filename="CS204_OS_Syllabus.txt",
        syllabus_id="syl_test_1"
    )

    assert len(subjects) >= 1
    assert any("operating systems" in s.lower() for s in subjects)
    assert len(books) >= 3

    # Check Silberschatz book
    silber = next((b for b in books if "operating system concepts" in b.title.lower()), None)
    assert silber is not None
    assert "Silberschatz" in silber.author
    assert silber.edition == "10th Edition"
    assert silber.year == 2018
    assert silber.publisher == "Wiley"
    assert silber.isbn == "978-1119456339"
    assert silber.confidence >= 0.85
    assert silber.book_type == BookType.TEXTBOOK
    assert silber.page_number == 1
    assert silber.context_snippet is not None

    # Check Tanenbaum reference book
    tanen = next((b for b in books if "modern operating systems" in b.title.lower()), None)
    assert tanen is not None
    assert tanen.book_type == BookType.REFERENCE


def test_syllabus_citation_varieties_apa_harvard_and_multi_authors():
    """Verify robust extraction of APA, Harvard, multi-author comma, and quoted-with-by styles."""
    apa_line = 'Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2009). Introduction to Algorithms (3rd ed.). MIT Press.'
    rec_apa = syllabus_extractor._parse_citation_line(apa_line, "syl_apa", "Algorithms", BookType.TEXTBOOK, 1)
    assert rec_apa is not None
    assert "Introduction to Algorithms" in rec_apa.title
    assert "Cormen" in rec_apa.author
    assert rec_apa.year == 2009
    assert rec_apa.publisher == "MIT Press"

    multi_author_line = 'Silberschatz, Galvin, Gagne, Operating System Concepts, Wiley, 2018'
    rec_multi = syllabus_extractor._parse_citation_line(multi_author_line, "syl_multi", "OS", BookType.TEXTBOOK, 1)
    assert rec_multi is not None
    assert "Operating System Concepts" in rec_multi.title
    assert "Silberschatz" in rec_multi.author

    by_quote_line = '"The Design of the UNIX Operating System" by Maurice J. Bach, Prentice Hall, 1986.'
    rec_by = syllabus_extractor._parse_citation_line(by_quote_line, "syl_by", "OS", BookType.REFERENCE, 1)
    assert rec_by is not None
    assert "The Design of the UNIX Operating System" in rec_by.title
    assert rec_by.author == "Maurice J. Bach"
    assert rec_by.year == 1986


def test_syllabus_upload_and_management_api():
    """Test full syllabus upload, inspection, editing, and deletion API workflow."""
    file_bytes = io.BytesIO(SAMPLE_SYLLABUS_TEXT.encode("utf-8"))
    upload_resp = client.post(
        "/api/syllabus/upload",
        files={"file": ("syllabus.txt", file_bytes, "text/plain")}
    )
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    assert "syllabus_id" in data
    syl_id = data["syllabus_id"]
    assert data["total_extracted"] >= 3
    assert len(data["books"]) >= 3

    # Get syllabus details
    get_resp = client.get(f"/api/syllabus/{syl_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["syllabus_id"] == syl_id

    # Add a custom reference book
    new_book_id = "book_custom_test"
    new_book = {
        "id": new_book_id,
        "syllabus_id": syl_id,
        "title": "Introduction to Algorithms",
        "author": "Thomas H. Cormen, Charles E. Leiserson",
        "edition": "3rd ed.",
        "year": 2009,
        "publisher": "MIT Press",
        "isbn": "978-0262033848",
        "book_type": "REFERENCE",
        "subject": "Algorithms Module",
        "page_number": 2,
        "context_snippet": "Algorithms reference",
        "confidence": 0.95,
        "is_selected": True
    }
    add_resp = client.post(f"/api/syllabus/{syl_id}/books", json=new_book)
    assert add_resp.status_code == 200

    # Delete the book
    del_resp = client.delete(f"/api/syllabus/{syl_id}/books/{new_book_id}")
    assert del_resp.status_code == 200


def test_openstax_provider_search():
    """Verify OpenStax connector returns high-confidence peer-reviewed textbooks."""
    import asyncio
    q = BookSearchQuery(title="Calculus Volume 1", author="Gilbert Strang")
    results = asyncio.run(search_openstax(q, limit=2))

    assert len(results) >= 1
    top = results[0]
    assert "Calculus" in top.title
    assert "Gilbert Strang" in top.authors
    assert top.source_name == "OpenStax"
    assert top.licensing.is_legally_downloadable is True
    assert top.access_type == "FULL_TEXT"
    assert top.download_url is not None


def test_search_batch_lifecycle_and_filtering():
    """Test creating a batch search, retrieving status, and filtering."""
    # First upload a syllabus
    file_bytes = io.BytesIO(SAMPLE_SYLLABUS_TEXT.encode("utf-8"))
    upload_resp = client.post(
        "/api/syllabus/upload",
        files={"file": ("syllabus_batch.txt", file_bytes, "text/plain")}
    )
    syl_id = upload_resp.json()["syllabus_id"]

    # Start batch
    batch_resp = client.post(f"/api/syllabus/{syl_id}/search-batch")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert "batch_id" in batch_data
    batch_id = batch_data["batch_id"]
    assert batch_data["total_books"] >= 3

    # Query batch status
    status_resp = client.get(f"/api/batches/{batch_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["batch_id"] == batch_id

    # Filter batch status by ALL
    filter_resp = client.get(f"/api/batches/{batch_id}?filter=ALL")
    assert filter_resp.status_code == 200


def test_alternative_finder_endpoint():
    """Test finding open alternatives for a commercial candidate."""
    # Create and persist a mock commercial candidate
    from app.schemas import BookCandidate, LicensingEvidence, LicenseStatus
    cid = "cand_comm_test_ai"
    lic = LicensingEvidence(
        status=LicenseStatus.NOT_ELIGIBLE,
        license_name="Commercial In-Copyright",
        rights_statement="All rights reserved by Pearson.",
        source_url="https://books.google.com/books?id=test",
        verified_at="2026-10-26T00:00:00Z",
        is_legally_downloadable=False
    )
    cand = BookCandidate(
        candidate_id=cid,
        title="Artificial Intelligence: A Modern Approach",
        authors=["Stuart Russell", "Peter Norvig"],
        publisher="Pearson",
        published_year=2020,
        categories=["Computer Science", "Artificial Intelligence"],
        source_name="Google Books",
        source_url="https://books.google.com/books?id=test",
        licensing=lic
    )
    query = BookSearchQuery(title="Artificial Intelligence")
    repository.save_search("srch_alt_test", query, [cand])

    # Query alternative endpoint
    resp = client.get(f"/api/candidates/{cid}/alternative")
    assert resp.status_code == 200
    data = resp.json()
    assert data["original_candidate_id"] == cid
    assert data["original_licensing_status"] == LicenseStatus.NOT_ELIGIBLE.value
    assert "alternatives" in data


def test_acquisition_history_endpoint():
    """Verify unified acquisition history returns records with filter support."""
    resp = client.get("/api/history?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_records" in data
    assert "records" in data

    # Test filtering by record_type
    resp_search = client.get("/api/history?record_type=SEARCH&limit=5")
    assert resp_search.status_code == 200
    for rec in resp_search.json()["records"]:
        assert rec["record_type"] == "SEARCH"
