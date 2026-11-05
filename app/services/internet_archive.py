import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from app.config import settings
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    AccessState,
    AccessClassification,
    LicenseStatus,
    LicensingEvidence
)
from app.services.resilience import execute_with_backoff

logger = logging.getLogger(__name__)

USER_AGENT = "SyllExtract-BookAcquisitionAgent/3.2 (https://github.com/syll-extract; contact@syll-extract.org)"


def _clean_ia_query_term(text: str) -> str:
    """Sanitize query terms for Internet Archive Lucene syntax."""
    if not text:
        return ""
    # Strip characters that break Lucene syntax
    cleaned = re.sub(r'[\/\\:;!?"\(\)\[\]\{\}\^~*?+]', ' ', text)
    return " ".join(cleaned.split())


async def search_internet_archive(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search Internet Archive catalog for legitimate public-domain monographs
    and clearly distinguish downloadable items from Controlled Digital Lending (CDL).
    """
    candidates: List[BookCandidate] = []

    # Build Lucene query
    q_parts = ["mediatype:(texts)"]

    if query.title:
        clean_title = _clean_ia_query_term(query.title)
        q_parts.append(f'(title:"{clean_title}" OR "{clean_title}")')

    if query.author:
        clean_author = _clean_ia_query_term(query.author)
        q_parts.append(f'(creator:"{clean_author}" OR "{clean_author}")')

    if query.isbn:
        clean_isbn = re.sub(r"[^0-9Xx]", "", query.isbn)
        if clean_isbn:
            q_parts.append(f'("{clean_isbn}")')

    if not query.title and not query.author and not query.isbn and query.q:
        clean_q = _clean_ia_query_term(query.q)
        if clean_q:
            q_parts.append(f'("{clean_q}")')

    if len(q_parts) == 1:
        return []

    full_lucene_query = " AND ".join(q_parts)
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": full_lucene_query,
        "fl[]": [
            "identifier", "title", "creator", "year", "publicdate",
            "licenseurl", "publicdomain", "collection", "downloads",
            "format", "language", "description", "publisher"
        ],
        "rows": str(min(limit, 10)),
        "output": "json"
    }
    headers = {"User-Agent": USER_AGENT}

    async def _do_search():
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    try:
        data = await execute_with_backoff("Internet Archive", _do_search, max_retries=1)
    except Exception as e:
        logger.warning(f"Internet Archive search failed: {e}")
        raise e

    response_block = data.get("response", {})
    docs = response_block.get("docs", [])
    now_iso = datetime.now(timezone.utc).isoformat()

    for doc in docs:
        identifier = doc.get("identifier")
        if not identifier:
            continue

        raw_title = doc.get("title")
        if isinstance(raw_title, list):
            title = raw_title[0] if raw_title else "Untitled"
        else:
            title = str(raw_title or "Untitled")

        # Parse creator/author
        raw_creator = doc.get("creator")
        if isinstance(raw_creator, list):
            authors = [str(a).strip() for a in raw_creator if a]
        elif raw_creator:
            authors = [str(raw_creator).strip()]
        else:
            authors = []

        # Parse year
        year_val = doc.get("year")
        pub_year: Optional[int] = None
        if year_val:
            try:
                pub_year = int(str(year_val)[:4])
            except (ValueError, TypeError):
                pub_year = None

        publisher = doc.get("publisher")
        if isinstance(publisher, list):
            publisher = publisher[0] if publisher else None

        collections = doc.get("collection", [])
        if isinstance(collections, str):
            collections = [collections]

        col_str = " ".join(collections).lower()
        license_url = str(doc.get("licenseurl", "")).lower()
        is_public_domain_flag = bool(doc.get("publicdomain", False))
        is_pre_1929 = pub_year is not None and pub_year < 1929

        # Distinguish CDL / Borrowing from downloadable public domain
        is_cdl = "inlibrary" in col_str or "printdisabled" in col_str or "lending" in col_str
        is_public_domain = (
            not is_cdl
            and (
                is_pre_1929
                or is_public_domain_flag
                or "gutenberg" in col_str
                or "publicdomain" in license_url
                or "creativecommons.org/publicdomain" in license_url
                or "creativecommons.org/licenses/by" in license_url
            )
        )

        source_url = f"https://archive.org/details/{identifier}"
        embed_url = f"https://archive.org/embed/{identifier}"
        reader_url = source_url
        thumbnail_url = f"https://archive.org/services/img/{identifier}"
        can_embed = True

        evidence_details = [
            f"Cataloged in Internet Archive repository (identifier: {identifier}).",
            f"Collections: {', '.join(collections[:3]) if collections else 'general'}."
        ]

        if is_public_domain:
            access_state = AccessState.AUTHORIZED_DOWNLOAD
            access_classification = AccessClassification.AUTHORIZED_FREE_PDF
            access_type = "FULL_TEXT"
            access_msg = "Verified public domain text available for online reading and authorized PDF download."
            reader_type = "FULL_READER"
            download_url = f"https://archive.org/download/{identifier}/{identifier}.pdf"
            pdf_url = download_url
            epub_url = f"https://archive.org/download/{identifier}/{identifier}.epub"
            book_format = "PDF"

            evidence_details.extend([
                "Verified Public Domain or Creative Commons licensed content.",
                "Authorized for academic digital viewing and full text acquisition."
            ])

            licensing = LicensingEvidence(
                status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
                license_name="Public Domain / Open Access (Internet Archive)",
                rights_statement=doc.get("licenseurl") or "Public Domain Mark 1.0 / Open Access",
                source_url=source_url,
                terms_url="https://archive.org/about/terms.php",
                evidence_details=evidence_details,
                verified_at=now_iso,
                intended_use="educational_reference_acquisition",
                is_legally_downloadable=True
            )
        elif is_cdl:
            access_state = AccessState.BORROWING_REQUIRED
            access_classification = AccessClassification.BORROWING_OR_LOGIN_REQUIRED
            access_type = "PREVIEW"
            access_msg = "Read Online / Preview Only: Controlled Digital Lending copy on Internet Archive. Online borrowing in Reading Workspace only; downloading prohibited."
            reader_type = "FULL_READER"
            download_url = None
            pdf_url = None
            epub_url = None
            book_format = "BORROW_REQUIRED"

            evidence_details.extend([
                "Identified under Controlled Digital Lending (CDL) loan collection.",
                "Mandatory anti-piracy safeguard: Permanent file downloading is strictly blocked."
            ])

            licensing = LicensingEvidence(
                status=LicenseStatus.NOT_ELIGIBLE,
                license_name="Controlled Digital Lending (Borrow-Only)",
                rights_statement="Controlled digital lending loan. No permanent file download permitted.",
                source_url=source_url,
                terms_url="https://archive.org/about/terms.php",
                evidence_details=evidence_details,
                verified_at=now_iso,
                intended_use="educational_reference_acquisition",
                is_legally_downloadable=False
            )
        else:
            # Rights unclear or general viewable
            access_state = AccessState.RIGHTS_UNCLEAR
            access_classification = AccessClassification.ACCESS_STATUS_UNKNOWN
            access_type = "PREVIEW"
            access_msg = "Internet Archive digital item. Licensing rights unconfirmed; human review required before acquisition."
            reader_type = "PREVIEW_ONLY"
            download_url = None
            pdf_url = None
            epub_url = None
            book_format = "PREVIEW_ONLY"

            evidence_details.append("Rights metadata is unverified or ambiguous.")

            licensing = LicensingEvidence(
                status=LicenseStatus.NEEDS_REVIEW,
                license_name="Unconfirmed Rights (Internet Archive)",
                rights_statement="Licensing terms require institutional review.",
                source_url=source_url,
                terms_url="https://archive.org/about/terms.php",
                evidence_details=evidence_details,
                verified_at=now_iso,
                intended_use="educational_reference_acquisition",
                is_legally_downloadable=False
            )

        candidate = BookCandidate(
            candidate_id=f"cand_ia_{identifier}",
            title=title,
            authors=authors,
            publisher=publisher,
            published_year=pub_year,
            edition="Internet Archive Digitized Edition",
            isbns=[],
            page_count=None,
            language=doc.get("language", "en") if isinstance(doc.get("language"), str) else "en",
            categories=collections[:3],
            description=f"Internet Archive item #{identifier}. Downloads: {doc.get('downloads', 0)}",
            thumbnail_url=thumbnail_url,
            source_name="Internet Archive",
            source_url=source_url,
            reader_url=reader_url,
            embed_url=embed_url,
            preview_url=source_url if access_state != AccessState.AUTHORIZED_DOWNLOAD else None,
            pdf_url=pdf_url,
            epub_url=epub_url,
            access_state=access_state,
            access_classification=access_classification,
            access_type=access_type,
            access_message=access_msg,
            reader_type=reader_type,
            can_embed=can_embed,
            download_url=download_url,
            format=book_format,
            is_open_access=is_public_domain,
            licensing=licensing
        )
        candidates.append(candidate)

    return candidates
