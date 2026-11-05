from typing import Dict, Any, Optional
from pathlib import Path


class SyllExtractImportAdapter:
    """
    Adapter formatting verified reference book acquisition artifacts
    for later ingestion by SyllExtract's reference_book_indexer.py.
    Operates independently to guarantee zero disruption to existing code.
    """

    @staticmethod
    def format_for_reference_book_indexer(provenance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a standardized payload matching the reference book indexer specification.
        """
        file_path = provenance.get("file_path", "")
        file_name = Path(file_path).name if file_path else "book.pdf"

        # Generate a clean syllabus citation reference key
        authors = provenance.get("authors", [])
        first_author = authors[0].split()[-1] if authors else "Author"
        year = provenance.get("published_year") or "ND"
        citation_key = f"{first_author}_{year}".lower()

        return {
            "book_id": provenance.get("candidate_id"),
            "citation_key": citation_key,
            "title": provenance.get("title"),
            "authors": authors,
            "publisher": provenance.get("publisher"),
            "publication_year": provenance.get("published_year"),
            "edition": provenance.get("edition"),
            "isbns": provenance.get("isbns", []),
            "file_metadata": {
                "file_path": file_path,
                "file_name": file_name,
                "sha256_hash": provenance.get("file_hash"),
                "file_size_bytes": provenance.get("file_size_bytes"),
                "page_count": provenance.get("page_count"),
                "format": "PDF"
            },
            "legal_provenance": {
                "source_name": provenance.get("source_name"),
                "source_url": provenance.get("source_url"),
                "license_status": provenance.get("license_status"),
                "license_name": provenance.get("license_name"),
                "approval_id": provenance.get("approval_id"),
                "acquired_at": provenance.get("acquired_at"),
                "intended_use": provenance.get("intended_use")
            },
            "syll_extract_indexer_ready": True,
            "compatible_extractors": [
                "extractors/reference_book_indexer.py",
                "extractors/topic_finder.py"
            ]
        }


import_adapter = SyllExtractImportAdapter()
