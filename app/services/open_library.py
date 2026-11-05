import logging
import re
from typing import List, Optional
from urllib.parse import quote_plus
import httpx
from app.config import settings
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    AccessState,
    AccessClassification,
    LicenseStatus
)
from app.services.licensing_verifier import verify_licensing
from app.services.resilience import execute_with_backoff

logger = logging.getLogger(__name__)

USER_AGENT = "SyllExtract-BookAcquisitionAgent/3.2 (https://github.com/syll-extract; academic-bot@syll-extract.org)"


async def search_open_library(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search Open Library Search API (https://openlibrary.org/search.json) for metadata,
    editions, covers, and lending/open access statuses.
    Respects rate limits, includes custom User-Agent, and treats availability indicatively.
    """
    params = {
        "limit": min(limit, 10),
        "fields": "key,title,author_name,publisher,first_publish_year,edition_count,isbn,subject,cover_i,ia,lending_identifier_s,ia_collection_s,public_scan_b,ebook_access_s,number_of_pages_median,language"
    }
    if query.isbn:
        params["isbn"] = query.isbn.strip()
    elif query.title and query.author:
        params["title"] = query.title.strip()
        params["author"] = query.author.strip()
    elif query.q and query.q.strip():
        q_clean = query.q.strip()
        digit_only = re.sub(r"[^0-9Xx]", "", q_clean)
        if len(digit_only) in (10, 13):
            params["isbn"] = digit_only
        else:
            params["q"] = q_clean
    elif query.title:
        params["title"] = query.title.strip()
    elif query.author:
        params["author"] = query.author.strip()

    if not any(k in params for k in ("isbn", "title", "author", "q")):
        params["q"] = "book"

    url = "https://openlibrary.org/search.json"
    headers = {"User-Agent": USER_AGENT}

    async def _do_fetch():
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    try:
        data = await execute_with_backoff("Open Library", _do_fetch, max_retries=1)
    except Exception as e:
        logger.warning(f"Error querying Open Library: {e}")
        raise e

    candidates: List[BookCandidate] = []
    docs = data.get("docs", [])

    for doc in docs[:limit]:
        ol_key = doc.get("key", "").replace("/works/", "ol_work_")
        if not ol_key:
            ol_key = f"ol_{doc.get('cover_edition_key', 'unknown')}"

        title = doc.get("title", "Untitled")
        authors = doc.get("author_name", [])
        publisher_list = doc.get("publisher", [])
        publisher = publisher_list[0] if publisher_list else None
        first_publish_year = doc.get("first_publish_year")
        edition_count = doc.get("edition_count")
        edition_str = f"{edition_count} editions" if edition_count else None
        isbns = doc.get("isbn", [])[:5]

        subtitle = doc.get("subtitle")
        categories = (doc.get("subject", []) or [])[:5]
        isbn_10 = None
        isbn_13 = None
        for i in isbns:
            cleaned_i = i.replace("-", "").strip()
            if len(cleaned_i) == 10 and not isbn_10:
                isbn_10 = i
            elif len(cleaned_i) == 13 and not isbn_13:
                isbn_13 = i

        cover_id = doc.get("cover_i")
        thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None

        work_path = doc.get("key", "")
        source_url = f"https://openlibrary.org{work_path}" if work_path else "https://openlibrary.org"

        # Extract Internet Archive / Reader details
        ia_list = doc.get("ia", [])
        ia_id = ia_list[0] if ia_list else None
        public_scan = doc.get("public_scan_b", False)
        ebook_access = doc.get("ebook_access_s", "no_ebook")
        has_lending = bool(doc.get("lending_identifier_s"))

        # External library search link
        ext_search_url = f"https://openlibrary.org/search?q={quote_plus(title + ' ' + (authors[0] if authors else ''))}"

        # Evaluate Access State indicatively
        is_pre_1929 = first_publish_year is not None and first_publish_year < 1929
        is_public_domain_oa = bool(ia_id and (public_scan or is_pre_1929 or ebook_access == "public"))

        if is_public_domain_oa:
            reader_url = f"https://archive.org/details/{ia_id}"
            embed_url = f"https://archive.org/embed/{ia_id}"
            preview_url = None
            pdf_url = f"https://archive.org/download/{ia_id}/{ia_id}.pdf"
            download_url = pdf_url
            access_state = AccessState.AUTHORIZED_DOWNLOAD
            access_classification = AccessClassification.AUTHORIZED_FREE_PDF
            access_type = "FULL_TEXT"
            access_message = "Verified public domain scan available to read on Internet Archive with authorized PDF."
            reader_type = "FULL_READER"
            can_embed = True
            book_format = "PDF"
        elif ia_id or has_lending or ebook_access == "borrowable":
            resolved_ia = ia_id or "borrowable"
            reader_url = f"https://archive.org/details/{resolved_ia}" if ia_id else source_url
            embed_url = f"https://archive.org/embed/{ia_id}" if ia_id else None
            preview_url = reader_url
            pdf_url = None
            download_url = None
            access_state = AccessState.BORROWING_REQUIRED
            access_classification = AccessClassification.BORROWING_OR_LOGIN_REQUIRED
            access_type = "PREVIEW"
            access_message = "Read Online / Preview Only: Controlled digital lending copy via Open Library & Internet Archive. Direct file downloading is prohibited."
            reader_type = "FULL_READER" if embed_url else "PREVIEW_ONLY"
            can_embed = bool(embed_url)
            book_format = "BORROW_REQUIRED"
        elif ebook_access == "printdisabled":
            reader_url = source_url
            embed_url = None
            preview_url = None
            pdf_url = None
            download_url = None
            access_state = AccessState.LOGIN_REQUIRED
            access_classification = AccessClassification.BORROWING_OR_LOGIN_REQUIRED
            access_type = "PREVIEW"
            access_message = "Access restricted to patrons with qualifying print disabilities."
            reader_type = "OFFICIAL_PAGE"
            can_embed = False
            book_format = "PRINT_DISABLED"
        else:
            reader_url = source_url
            embed_url = None
            preview_url = None
            pdf_url = None
            download_url = None
            access_state = AccessState.UNAVAILABLE
            access_classification = AccessClassification.NO_READABLE_COPY_FOUND
            access_type = "PUBLISHER_PAGE"
            access_message = "Open Library catalog record. Direct digital reader is not cataloged for this edition."
            reader_type = "OFFICIAL_PAGE"
            can_embed = False
            book_format = "PREVIEW_ONLY"

        # Verify licensing independently
        licensing = await verify_licensing(
            source_name="Open Library",
            source_url=source_url,
            title=title,
            published_year=first_publish_year,
            open_library_details=doc
        )

        candidate = BookCandidate(
            candidate_id=f"cand_ol_{ol_key.replace('/', '_')}",
            title=title,
            subtitle=subtitle,
            authors=authors,
            publisher=publisher,
            published_year=first_publish_year,
            edition=edition_str,
            isbns=isbns,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            page_count=doc.get("number_of_pages_median"),
            language=doc.get("language", ["en"])[0] if doc.get("language") else "en",
            categories=categories,
            description=f"Cataloged in Open Library with {edition_count or 1} edition(s)." if edition_count else "Cataloged in Open Library.",
            thumbnail_url=thumbnail,
            source_name="Open Library",
            source_url=source_url,
            reader_url=reader_url,
            embed_url=embed_url,
            external_search_url=ext_search_url,
            preview_url=preview_url,
            pdf_url=pdf_url,
            access_state=access_state,
            access_classification=access_classification,
            access_type=access_type,
            access_message=access_message,
            reader_type=reader_type,
            can_embed=can_embed,
            download_url=None,  # Lending/preview only: direct download prohibited
            format=book_format,
            is_open_access=False,  # Path B: Lending & Digital Preview Only
            licensing=licensing
        )
        candidates.append(candidate)

    return candidates
