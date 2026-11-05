import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import quote_plus
import httpx
from app.config import settings
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    AccessState,
    AccessClassification
)
from app.services.licensing_verifier import verify_licensing
from app.services.resilience import execute_with_backoff

logger = logging.getLogger(__name__)

USER_AGENT = "SyllExtract-BookAcquisitionAgent/3.2 (https://github.com/syll-extract; academic-bot@syll-extract.org)"

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/terms",
    "gbs": "http://schemas.google.com/books/2008",
    "gd": "http://schemas.google.com/g/2005"
}


def _extract_year(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    match = re.search(r"\b(1\d\d\d|20\d\d)\b", date_str)
    return int(match.group(1)) if match else None


async def _search_google_books_atom(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search official Google Books GData/Atom feed (https://books.google.com/books/feeds/volumes).
    High-reliability endpoint: no IP daily rate limiting, fast response, complete metadata.
    """
    query_parts = []
    if query.isbn:
        query_parts.append(query.isbn.strip())
    if query.title:
        query_parts.append(query.title.strip())
    if query.author:
        query_parts.append(query.author.strip())
    if query.q and not query_parts:
        query_parts.append(query.q.strip())

    q_str = " ".join(query_parts) if query_parts else (query.title or "books")

    url = "https://books.google.com/books/feeds/volumes"
    params = {
        "q": q_str,
        "max-results": min(limit, 10),
    }
    headers = {"User-Agent": USER_AGENT}

    async def _do_fetch_feed():
        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.text

    feed_text = await execute_with_backoff("Google Books GData", _do_fetch_feed, max_retries=1)

    root = ET.fromstring(feed_text)
    candidates: List[BookCandidate] = []

    for entry in root.findall("atom:entry", ATOM_NS)[:limit]:
        title_el = entry.find("atom:title", ATOM_NS)
        title = title_el.text if title_el is not None and title_el.text else "Untitled"

        authors = [a.text for a in entry.findall("dc:creator", ATOM_NS) if a.text]
        publisher_el = entry.find("dc:publisher", ATOM_NS)
        publisher = publisher_el.text if publisher_el is not None else None
        date_el = entry.find("dc:date", ATOM_NS)
        date_str = date_el.text if date_el is not None else None
        year = _extract_year(date_str)

        desc_el = entry.find("dc:description", ATOM_NS)
        description = desc_el.text if desc_el is not None else None

        subjects = [s.text for s in entry.findall("dc:subject", ATOM_NS) if s.text]

        # Extract identifiers & ISBNs
        identifiers = [i.text for i in entry.findall("dc:identifier", ATOM_NS) if i.text]
        v_id = None
        isbns = []
        isbn_10 = None
        isbn_13 = None
        for ident in identifiers:
            if ident.startswith("ISBN:"):
                clean_isbn = ident[5:].strip()
                isbns.append(clean_isbn)
                if len(clean_isbn) == 10 and not isbn_10:
                    isbn_10 = clean_isbn
                elif len(clean_isbn) == 13 and not isbn_13:
                    isbn_13 = clean_isbn
            elif not v_id:
                v_id = ident

        if not v_id:
            id_el = entry.find("atom:id", ATOM_NS)
            if id_el is not None and id_el.text:
                v_id = id_el.text.split("/")[-1]

        # Links
        thumbnail = None
        info_link = None
        preview_link = None
        for link in entry.findall("atom:link", ATOM_NS):
            rel = link.get("rel", "")
            href = link.get("href", "")
            if "thumbnail" in rel:
                thumbnail = href
            elif "info" in rel:
                info_link = href
            elif "preview" in rel:
                preview_link = href

        source_url = info_link or f"https://books.google.com/books?id={v_id}"

        # Viewability & Embeddability
        view_el = entry.find("gbs:viewability", ATOM_NS)
        view_val = view_el.get("value", "") if view_el is not None else ""
        open_el = entry.find("gbs:openAccess", ATOM_NS)
        open_val = open_el.get("value", "") if open_el is not None else ""
        embed_el = entry.find("gbs:embeddability", ATOM_NS)
        embed_val = embed_el.get("value", "") if embed_el is not None else ""

        can_embed = "embeddable" in embed_val or "view_partial" in view_val or "view_all" in view_val
        embed_url = f"https://books.google.com/books?id={v_id}&output=embed" if can_embed and v_id else None

        is_open_access = "enabled" in open_val or "view_all" in view_val or (year and year < 1929)

        if is_open_access:
            access_state = AccessState.FULL_TEXT_ONLINE
            access_classification = AccessClassification.FULL_TEXT_READABLE_ONLINE_NO_DOWNLOAD
            access_type = "FULL_TEXT"
            access_message = "Google Books confirmed open-access volume readable online via Google Web Reader."
            reader_type = "FULL_READER"
            reader_url = preview_link or source_url
            download_url = None
            pdf_url = None
            epub_url = None
            book_format = "PREVIEW_ONLY"
        elif "view_partial" in view_val:
            access_state = AccessState.PREVIEW_ONLY
            access_classification = AccessClassification.LIMITED_PREVIEW
            access_type = "PREVIEW"
            access_message = "Read Online / Preview Only: Google Books authorized preview. Digital file downloading prohibited."
            reader_type = "PREVIEW_ONLY"
            reader_url = preview_link or source_url
            download_url = None
            pdf_url = None
            epub_url = None
            book_format = "PREVIEW_ONLY"
        else:
            access_state = AccessState.COMMERCIAL_ACCESS
            access_classification = AccessClassification.COMMERCIAL_ACCESS_REQUIRED
            access_type = "PUBLISHER_PAGE"
            access_message = "In-copyright commercial work. Access requires purchase or institutional licensing."
            reader_type = "OFFICIAL_PAGE"
            reader_url = source_url
            download_url = None
            pdf_url = None
            epub_url = None
            book_format = "PREVIEW_ONLY"

        licensing = await verify_licensing(
            source_name="Google Books",
            source_url=source_url,
            title=title,
            published_year=year,
            raw_rights="Public Domain" if is_open_access else "All Rights Reserved"
        )

        cand = BookCandidate(
            candidate_id=f"cand_gb_{v_id or 'unknown'}",
            title=title,
            authors=authors,
            publisher=publisher,
            published_year=year,
            isbns=isbns,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            categories=subjects[:5],
            description=description,
            thumbnail_url=thumbnail,
            source_name="Google Books",
            source_url=source_url,
            reader_url=reader_url,
            embed_url=embed_url,
            external_search_url=source_url,
            preview_url=preview_link,
            pdf_url=pdf_url,
            epub_url=epub_url,
            access_state=access_state,
            access_classification=access_classification,
            access_type=access_type,
            access_message=access_message,
            reader_type=reader_type,
            can_embed=can_embed,
            download_url=download_url,
            format=book_format,
            is_open_access=is_open_access,
            licensing=licensing
        )
        candidates.append(cand)

    return candidates


async def search_google_books(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search Google Books API.
    Attempts JSON v1 API if an API key is configured.
    Seamlessly falls back to official Google Books GData/Atom feed if the v1 API is rate-limited (HTTP 429)
    or if no API key is set.
    """
    # If API key is available, attempt JSON API
    if settings.GOOGLE_BOOKS_API_KEY:
        query_parts = []
        if query.isbn:
            query_parts.append(f"isbn:{query.isbn.strip()}")
        if query.title:
            query_parts.append(f"intitle:{query.title.strip()}")
        if query.author:
            query_parts.append(f"inauthor:{query.author.strip()}")
        if query.q and not query_parts:
            q_clean = query.q.strip()
            digit_only = re.sub(r"[^0-9Xx]", "", q_clean)
            if len(digit_only) in (10, 13):
                query_parts.append(f"isbn:{digit_only}")
            else:
                query_parts.append(q_clean)

        q_str = " ".join(query_parts) if query_parts else (query.title or "books")

        params = {
            "q": q_str,
            "maxResults": min(limit, 10),
            "printType": "books",
            "key": settings.GOOGLE_BOOKS_API_KEY
        }
        url = "https://www.googleapis.com/books/v1/volumes"
        headers = {"User-Agent": USER_AGENT}

        async def _do_fetch_json():
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()

        try:
            data = await execute_with_backoff("Google Books", _do_fetch_json, max_retries=1)
            items = data.get("items", [])
            candidates: List[BookCandidate] = []
            for item in items:
                v_id = item.get("id", "gb_unknown")
                info = item.get("volumeInfo", {})
                access = item.get("accessInfo", {})

                title = info.get("title", "Untitled")
                authors = info.get("authors", [])
                publisher = info.get("publisher")
                published_date = info.get("publishedDate")
                year = _extract_year(published_date)
                page_count = info.get("pageCount")
                description = info.get("description")
                source_url = info.get("infoLink") or f"https://books.google.com/books?id={v_id}"

                web_reader_link = access.get("webReaderLink")
                preview_link = info.get("previewLink")
                public_domain = access.get("publicDomain", False)
                viewability = access.get("viewability", "NO_PAGES")

                can_embed = viewability in ("PARTIAL", "ALL_PAGES") or public_domain
                embed_url = f"https://books.google.com/books?id={v_id}&output=embed" if can_embed else None

                pdf_download = access.get("pdf", {}).get("downloadLink") if access.get("pdf", {}).get("isAvailable") else None
                epub_download = access.get("epub", {}).get("downloadLink") if access.get("epub", {}).get("isAvailable") else None

                if public_domain and pdf_download:
                    access_state = AccessState.AUTHORIZED_DOWNLOAD
                    access_classification = AccessClassification.AUTHORIZED_FREE_PDF
                    access_type = "FULL_TEXT"
                    access_message = "Google Books confirmed public domain volume with authorized PDF download."
                    reader_type = "FULL_READER"
                    reader_url = web_reader_link or preview_link or source_url
                    download_url = pdf_download
                    pdf_url = pdf_download
                    epub_url = epub_download
                    book_format = "PDF"
                elif public_domain and web_reader_link:
                    access_state = AccessState.FULL_TEXT_ONLINE
                    access_classification = AccessClassification.FULL_TEXT_READABLE_ONLINE_NO_DOWNLOAD
                    access_type = "FULL_TEXT"
                    access_message = "Google Books public domain web reader (full text readable online)."
                    reader_type = "FULL_READER"
                    reader_url = web_reader_link
                    download_url = None
                    pdf_url = None
                    epub_url = None
                    book_format = "PREVIEW_ONLY"
                elif preview_link and viewability in ("PARTIAL", "ALL_PAGES"):
                    access_state = AccessState.PREVIEW_ONLY
                    access_classification = AccessClassification.LIMITED_PREVIEW
                    access_type = "PREVIEW"
                    access_message = f"Read Online / Preview Only: Google Books authorized {viewability.lower().replace('_', ' ')} preview. Direct file downloading prohibited."
                    reader_type = "PREVIEW_ONLY"
                    reader_url = preview_link
                    download_url = None
                    pdf_url = None
                    epub_url = None
                    book_format = "PREVIEW_ONLY"
                else:
                    access_state = AccessState.COMMERCIAL_ACCESS
                    access_classification = AccessClassification.COMMERCIAL_ACCESS_REQUIRED
                    access_type = "PUBLISHER_PAGE"
                    access_message = "In-copyright commercial volume. Purchase or bookstore access required."
                    reader_type = "OFFICIAL_PAGE"
                    reader_url = source_url
                    download_url = None
                    pdf_url = None
                    epub_url = None
                    book_format = "PREVIEW_ONLY"

                licensing = await verify_licensing(
                    source_name="Google Books",
                    source_url=source_url,
                    title=title,
                    published_year=year,
                    google_volume_info=info
                )

                isbns = []
                isbn_10 = None
                isbn_13 = None
                for ident in info.get("industryIdentifiers", []):
                    i_type = ident.get("type")
                    i_val = ident.get("identifier")
                    if i_val:
                        isbns.append(i_val)
                        if i_type == "ISBN_10" and not isbn_10:
                            isbn_10 = i_val
                        elif i_type == "ISBN_13" and not isbn_13:
                            isbn_13 = i_val

                cand = BookCandidate(
                    candidate_id=f"cand_gb_{v_id}",
                    title=title,
                    subtitle=info.get("subtitle"),
                    authors=authors,
                    publisher=publisher,
                    published_year=year,
                    published_date=published_date,
                    edition=None,
                    isbns=isbns,
                    isbn_10=isbn_10,
                    isbn_13=isbn_13,
                    page_count=page_count,
                    language=info.get("language", "en"),
                    categories=info.get("categories", [])[:5],
                    description=description,
                    thumbnail_url=info.get("imageLinks", {}).get("thumbnail") or info.get("imageLinks", {}).get("smallThumbnail"),
                    source_name="Google Books",
                    source_url=source_url,
                    reader_url=reader_url,
                    embed_url=embed_url,
                    external_search_url=source_url,
                    preview_url=preview_link,
                    pdf_url=pdf_url,
                    epub_url=epub_url,
                    access_state=access_state,
                    access_classification=access_classification,
                    access_type=access_type,
                    access_message=access_message,
                    reader_type=reader_type,
                    can_embed=can_embed,
                    download_url=download_url,
                    format=book_format,
                    is_open_access=bool(public_domain and pdf_download),
                    licensing=licensing
                )
                candidates.append(cand)
            return candidates
        except Exception as e:
            if "RATE_LIMITED" in str(e) or "429" in str(e):
                logger.info("Google Books v1 API rate-limited; switching to official Google Books GData feed.")
            else:
                logger.warning(f"Google Books v1 API error ({e}); switching to official Google Books GData feed.")

    # Primary or fallback: use official Google Books GData feed
    return await _search_google_books_atom(query, limit=limit)
