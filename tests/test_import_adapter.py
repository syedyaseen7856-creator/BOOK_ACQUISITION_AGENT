from app.services.import_adapter import import_adapter


def test_format_for_reference_book_indexer():
    provenance = {
        "job_id": "job_123",
        "candidate_id": "cand_doab_ostep",
        "title": "Operating Systems: Three Easy Pieces",
        "authors": ["Remzi H. Arpaci-Dusseau", "Andrea C. Arpaci-Dusseau"],
        "publisher": "Arpaci-Dusseau Books",
        "published_year": 2018,
        "edition": "Version 1.10",
        "isbns": ["9781985086593"],
        "page_count": 714,
        "file_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        "file_path": "D:/BOOK_ACQUISITION_AGENT/data/downloads/ostep.pdf",
        "file_size_bytes": 15420000,
        "source_name": "Directory of Open Access Books (DOAB)",
        "source_url": "https://pages.cs.wisc.edu/~remzi/OSTEP/",
        "license_status": "VERIFIED_FOR_PERMITTED_DOWNLOAD",
        "license_name": "Creative Commons CC-BY-NC-ND",
        "approval_id": "appr_987654321",
        "acquired_at": "2026-10-23T00:00:00Z",
        "intended_use": "educational_reference_acquisition"
    }

    payload = import_adapter.format_for_reference_book_indexer(provenance)

    assert payload["book_id"] == "cand_doab_ostep"
    assert "arpaci-dusseau_2018" in payload["citation_key"]
    assert payload["title"] == "Operating Systems: Three Easy Pieces"
    assert payload["file_metadata"]["page_count"] == 714
    assert payload["file_metadata"]["sha256_hash"] == provenance["file_hash"]
    assert payload["legal_provenance"]["license_status"] == "VERIFIED_FOR_PERMITTED_DOWNLOAD"
    assert payload["syll_extract_indexer_ready"] is True
    assert "extractors/reference_book_indexer.py" in payload["compatible_extractors"]
