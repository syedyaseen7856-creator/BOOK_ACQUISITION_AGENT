import logging
import re
from typing import List
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


async def _search_official_gutenberg(search_query: str, limit: int = 5) -> List[BookCandidate]:
    """
    Search official Project Gutenberg web search directly (https://www.gutenberg.org/ebooks/search/?query=...).
    Resilient primary/fallback when third-party Gutendex API is slow or times out.
    """
    encoded_q = quote_plus(search_query)
    url = f"https://www.gutenberg.org/ebooks/search/?query={encoded_q}"
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html_text = resp.text

    pattern = r'href="/ebooks/(\d+)".*?<span class="title">([^<]+)</span>.*?<span class="subtitle">([^<]*)</span>'
    matches = re.findall(pattern, html_text, re.DOTALL)

    candidates: List[BookCandidate] = []
    for g_id, raw_title, raw_author in matches[:limit]:
        title = " ".join(raw_title.strip().split())
        author_str = " ".join(raw_author.strip().split())
        authors = [author_str] if author_str else []

        epub_url = f"https://www.gutenberg.org/ebooks/{g_id}.epub3.images"
        pdf_url = f"https://www.gutenberg.org/ebooks/{g_id}.pdf"
        html_url = f"https://www.gutenberg.org/ebooks/{g_id}.html.images"
        thumbnail = f"https://www.gutenberg.org/cache/epub/{g_id}/pg{g_id}.cover.medium.jpg"
        source_url = f"https://www.gutenberg.org/ebooks/{g_id}"

        licensing = await verify_licensing(
            source_name="Project Gutenberg",
            source_url=source_url,
            title=title,
            published_year=None,
            raw_rights="Public domain in the USA."
        )

        cand = BookCandidate(
            candidate_id=f"cand_gut_{g_id}",
            title=title,
            authors=authors,
            publisher="Project Gutenberg",
            published_year=None,
            edition="Project Gutenberg Public Domain Edition",
            isbns=[],
            page_count=None,
            language="en",
            categories=["Classic Literature", "Public Domain"],
            description=f"Project Gutenberg official public-domain eBook #{g_id}.",
            thumbnail_url=thumbnail,
            source_name="Project Gutenberg",
            source_url=source_url,
            reader_url=html_url,
            embed_url=html_url,
            external_search_url=source_url,
            preview_url=None,
            pdf_url=pdf_url,
            epub_url=epub_url,
            access_state=AccessState.AUTHORIZED_DOWNLOAD,
            access_classification=AccessClassification.AUTHORIZED_FREE_EPUB,
            access_type="FULL_TEXT",
            access_message="Official public-domain edition. Complete text viewable online and authorized for download.",
            reader_type="HTML_READER",
            can_embed=True,
            download_url=epub_url,
            format="EPUB",
            is_open_access=True,
            licensing=licensing
        )
        candidates.append(cand)

    return candidates


async def search_gutenberg_repository(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search Project Gutenberg for confirmed public domain works.
    Retrieves official public domain ebook records and their available formats (EPUB, PDF, HTML, TXT).
    Uses official Gutenberg search with Gutendex fallback.
    """
    search_terms = []
    if query.q and query.q.strip():
        search_terms.append(query.q.strip())
    if query.title and query.title.strip() and query.title.strip() not in search_terms:
        search_terms.append(query.title.strip())
    if query.author and query.author.strip() and query.author.strip() not in search_terms:
        search_terms.append(query.author.strip())

    if not search_terms:
        return []

    search_query = " ".join(search_terms)

    # 1. Try official Project Gutenberg website search first (fast, authoritative, 0 rate limits)
    try:
        official_candidates = await execute_with_backoff(
            "Project Gutenberg",
            lambda: _search_official_gutenberg(search_query, limit=limit),
            max_retries=1
        )
        return official_candidates
    except Exception as e:
        logger.info(f"Official Gutenberg query failed ({e}); falling back to Gutendex.")

    # 2. Fallback to Gutendex API
    url = "https://gutendex.com/books/"
    params = {"search": search_query}
    headers = {"User-Agent": USER_AGENT}

    async def _do_fetch_gutendex():
        async with httpx.AsyncClient(timeout=4.0, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    try:
        data = await execute_with_backoff("Project Gutenberg Gutendex", _do_fetch_gutendex, max_retries=1)
    except Exception as e:
        logger.warning(f"Project Gutenberg query failed completely: {e}")
        raise e

    candidates: List[BookCandidate] = []
    results = data.get("results", [])

    for item in results[:limit]:
        g_id = item.get("id")
        title = item.get("title", "Untitled")

        authors = []
        for a in item.get("authors", []):
            name = a.get("name")
            if name:
                parts = [p.strip() for p in name.split(",")]
                if len(parts) == 2:
                    authors.append(f"{parts[1]} {parts[0]}")
                else:
                    authors.append(name)

        formats = item.get("formats", {})
        thumbnail = formats.get("image/jpeg")
        epub_url = formats.get("application/epub+zip")
        pdf_url = formats.get("application/pdf")
        txt_url = formats.get("text/plain; charset=us-ascii") or formats.get("text/plain")
        html_url = (
            formats.get("text/html")
            or formats.get("text/html; charset=utf-8")
            or f"https://www.gutenberg.org/ebooks/{g_id}.html.images"
        )

        download_url = epub_url or pdf_url or txt_url
        book_format = "EPUB" if epub_url else ("PDF" if pdf_url else "TXT")

        source_url = f"https://www.gutenberg.org/ebooks/{g_id}"
        reader_url = html_url
        embed_url = html_url
        reader_type = "HTML_READER"
        can_embed = True

        licensing = await verify_licensing(
            source_name="Project Gutenberg",
            source_url=source_url,
            title=title,
            published_year=None,
            raw_rights="Public domain in the USA."
        )

        categories = (item.get("subjects", []) or [])[:5]

        candidate = BookCandidate(
            candidate_id=f"cand_gut_{g_id}",
            title=title,
            authors=authors,
            publisher="Project Gutenberg",
            published_year=None,
            edition="Project Gutenberg Public Domain Edition",
            isbns=[],
            page_count=None,
            language=item.get("languages", ["en"])[0] if item.get("languages") else "en",
            categories=categories,
            description=f"Project Gutenberg eBook #{g_id}. Download count: {item.get('download_count', 0)}",
            thumbnail_url=thumbnail,
            source_name="Project Gutenberg",
            source_url=source_url,
            reader_url=reader_url,
            embed_url=embed_url,
            external_search_url=source_url,
            preview_url=None,
            pdf_url=pdf_url,
            epub_url=epub_url,
            access_state=AccessState.AUTHORIZED_DOWNLOAD,
            access_classification=AccessClassification.AUTHORIZED_FREE_EPUB if epub_url else AccessClassification.AUTHORIZED_FREE_PDF,
            access_type="FULL_TEXT",
            access_message="Official public-domain edition. Complete text viewable online and authorized for download.",
            reader_type=reader_type,
            can_embed=can_embed,
            download_url=download_url,
            format=book_format,
            is_open_access=True,
            licensing=licensing
        )
        candidates.append(candidate)

    return candidates
