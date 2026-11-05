import logging
import re
from typing import List, Optional
import httpx
from app.config import settings
from app.schemas import BookSearchQuery, BookCandidate
from app.services.licensing_verifier import verify_licensing

logger = logging.getLogger(__name__)


def _extract_year_from_crossref(item: dict) -> Optional[int]:
    for key in ("published-print", "published-online", "issued", "created"):
        date_parts = item.get(key, {}).get("date-parts", [])
        if date_parts and date_parts[0] and isinstance(date_parts[0][0], int):
            return date_parts[0][0]
    return None


async def search_crossref(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search Crossref REST API for verified academic books, monographs, and conference volumes.
    Polite API compliance adheres to Crossref guidelines.
    """
    search_terms = []
    if query.q and query.q.strip():
        search_terms.append(query.q.strip())
    if query.title and query.title.strip() and query.title.strip() not in search_terms:
        search_terms.append(query.title.strip())
    if query.author and query.author.strip() and query.author.strip() not in search_terms:
        search_terms.append(query.author.strip())

    if not search_terms and not query.isbn:
        return []

    params = {
        "rows": min(limit, 8),
    }

    if query.isbn:
        params["query.bibliographic"] = query.isbn.strip()
    elif search_terms:
        params["query.bibliographic"] = " ".join(search_terms)

    if query.title:
        params["query.title"] = query.title.strip()
    if query.author:
        params["query.author"] = query.author.strip()

    url = "https://api.crossref.org/works"
    headers = {
        "User-Agent": "SyllExtract-BookAcquisitionAgent/3.2 (educational reference acquisition; mailto:compliance@syllextract.local)"
    }

    candidates: List[BookCandidate] = []

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                raise RuntimeError("RATE_LIMITED: Crossref API rate limit reached.")
            if resp.status_code != 200:
                logger.warning(f"Crossref API returned {resp.status_code}: {resp.text[:120]}")
                raise RuntimeError(f"UNAVAILABLE: Crossref returned HTTP {resp.status_code}")

            data = resp.json()
            items = data.get("message", {}).get("items", [])

            for item in items[:limit]:
                doi = item.get("DOI", "")
                title_list = item.get("title", [])
                title = title_list[0] if title_list else "Untitled"

                subtitle_list = item.get("subtitle", [])
                subtitle = subtitle_list[0] if subtitle_list else None

                # Authors
                authors = []
                for a in item.get("author", []):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    name = f"{given} {family}".strip() if given or family else a.get("name", "")
                    if name and name not in authors:
                        authors.append(name)

                publisher = item.get("publisher")
                published_year = _extract_year_from_crossref(item)

                # ISBNs
                raw_isbns = item.get("ISBN", [])
                isbns = []
                isbn_10 = None
                isbn_13 = None
                for i in raw_isbns:
                    cleaned_i = re.sub(r"[^0-9Xx]", "", i).upper()
                    if cleaned_i:
                        isbns.append(cleaned_i)
                        if len(cleaned_i) == 10 and not isbn_10:
                            isbn_10 = cleaned_i
                        elif len(cleaned_i) == 13 and not isbn_13:
                            isbn_13 = cleaned_i

                # Categories / subjects
                categories = item.get("subject", [])[:5]

                doi_url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "https://crossref.org")
                source_url = doi_url

                # Check license information
                licenses = item.get("license", [])
                raw_rights = None
                terms_url = None
                if licenses:
                    first_lic = licenses[0]
                    raw_rights = first_lic.get("URL")
                    terms_url = first_lic.get("URL")

                licensing = await verify_licensing(
                    source_name="Crossref Academic Registry",
                    source_url=source_url,
                    title=title,
                    published_year=published_year,
                    raw_rights=raw_rights,
                    terms_url=terms_url
                )

                safe_doi_id = re.sub(r"[^a-zA-Z0-9_]", "_", doi) if doi else f"cr_{len(candidates)}"

                # Safely parse page count from strings like "133-149" or "10"
                raw_page = item.get("page")
                page_count_int = None
                if raw_page:
                    digits = re.findall(r"\d+", str(raw_page))
                    if digits:
                        if len(digits) >= 2 and "-" in str(raw_page):
                            try:
                                p1, p2 = int(digits[0]), int(digits[1])
                                page_count_int = (p2 - p1 + 1) if p2 >= p1 else int(digits[0])
                            except Exception:
                                page_count_int = int(digits[0])
                        else:
                            page_count_int = int(digits[0])

                candidate = BookCandidate(
                    candidate_id=f"cand_cr_{safe_doi_id[:40]}",
                    title=title,
                    subtitle=subtitle,
                    authors=authors,
                    publisher=publisher,
                    published_year=published_year,
                    edition=None,
                    isbns=isbns,
                    isbn_10=isbn_10,
                    isbn_13=isbn_13,
                    page_count=page_count_int,
                    language="en",
                    categories=categories,
                    description=f"Indexed in Crossref DOI registry ({doi}). Type: {item.get('type', 'book')}.",
                    thumbnail_url=None,
                    source_name="Crossref Academic Registry",
                    source_url=source_url,
                    reader_url=doi_url,
                    preview_url=doi_url,
                    pdf_url=None,
                    access_type="PUBLISHER_PAGE",
                    access_message="Official publisher / DOI landing page.",
                    reader_type="OFFICIAL_PAGE",
                    can_embed=False,
                    download_url=None,
                    format="CROSSREF_METADATA",
                    licensing=licensing
                )
                candidates.append(candidate)

    except RuntimeError as re_err:
        logger.warning(f"Crossref limitation: {re_err}")
        raise re_err
    except Exception as e:
        logger.warning(f"Error querying Crossref: {e}")

    return candidates
