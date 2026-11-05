import asyncio
import logging
import re
import time
import uuid
from typing import List, Tuple, Dict, Any, Optional
from app.config import settings
from urllib.parse import urlparse
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    ProviderStatus,
    AccessState,
    LicenseStatus
)
from app.db.repository import repository
from app.services.google_books import search_google_books
from app.services.open_library import search_open_library
from app.services.internet_archive import search_internet_archive
from app.services.authorized_repos import search_gutenberg_repository
from app.services.open_access_repos import search_openstax, search_doab
from app.services.authorized_web_discovery import search_authorized_web_discovery
from app.services.crossref import search_crossref
from app.services.web_search import load_mock_candidates
from app.services.confidence_scorer import calculate_confidence, _clean_str, _decompose_query_string
from app.services.resilience import search_cache, get_circuit_breaker

logger = logging.getLogger(__name__)

# Concurrency limiter: prevent connection spikes
PROVIDER_SEMAPHORE = asyncio.Semaphore(7)
PROVIDER_TIMEOUT_SECONDS = 12.0


def _is_approved_domain(url: Optional[str]) -> bool:
    if not url:
        return True
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        return any(
            hostname == d or hostname.endswith(f".{d}")
            for d in settings.allowed_domains_set
        )
    except Exception:
        return False


def _enforce_domain_guardrails(cand: BookCandidate) -> BookCandidate:
    """Enforce strict domain whitelisting on surfaced download and reader links."""
    if cand.download_url and not _is_approved_domain(cand.download_url):
        logger.warning(f"Domain guardrail stripped unapproved download_url: {cand.download_url}")
        cand.download_url = None
    if cand.pdf_url and not _is_approved_domain(cand.pdf_url):
        cand.pdf_url = None
    if cand.epub_url and not _is_approved_domain(cand.epub_url):
        cand.epub_url = None
    if cand.reader_url and not _is_approved_domain(cand.reader_url):
        cand.reader_url = cand.source_url if _is_approved_domain(cand.source_url) else None
    if cand.embed_url and not _is_approved_domain(cand.embed_url):
        cand.embed_url = None
        cand.can_embed = False
    return cand


def _normalize_edition_string(edition: Optional[str]) -> str:
    """Normalize edition string (e.g. '3rd Edition' -> '3')."""
    if not edition:
        return ""
    clean = edition.lower().strip()
    digits = re.findall(r"\d+", clean)
    if digits:
        return f"{digits[0]}ed"
    if "first" in clean:
        return "1ed"
    if "second" in clean:
        return "2ed"
    if "third" in clean:
        return "3ed"
    return clean[:12]


def _extract_primary_isbn(candidate: BookCandidate) -> str:
    """Extract clean 10 or 13 digit ISBN for deduplication comparison."""
    if candidate.isbn_13:
        return re.sub(r"[^0-9Xx]", "", candidate.isbn_13)
    if candidate.isbn_10:
        return re.sub(r"[^0-9Xx]", "", candidate.isbn_10)
    for i in candidate.isbns:
        c = re.sub(r"[^0-9Xx]", "", i)
        if len(c) in (10, 13):
            return c
    return ""


def _extract_author_surname(authors: List[str]) -> str:
    if not authors:
        return "unknown"
    first = authors[0].strip()
    parts = first.split()
    return parts[-1].lower() if parts else "unknown"


def _merge_candidates(primary: BookCandidate, secondary: BookCandidate) -> BookCandidate:
    """
    Intelligently merge metadata between identical book editions from different providers:
    - Retain authorized digital reader links and embed permissions
    - Retain verified download URLs (PDF/EPUB)
    - Elevate access state to the most permissive legitimate access
    - Merge ISBNs, alternate titles, and categories
    """
    # 1. Access State priority
    ACCESS_PRIORITY = {
        AccessState.AUTHORIZED_DOWNLOAD: 10,
        AccessState.FULL_TEXT_ONLINE: 8,
        AccessState.PREVIEW_ONLY: 6,
        AccessState.BORROWING_REQUIRED: 5,
        AccessState.LOGIN_REQUIRED: 4,
        AccessState.RIGHTS_UNCLEAR: 3,
        AccessState.COMMERCIAL_ACCESS: 2,
        AccessState.UNAVAILABLE: 1,
    }

    pri_p = ACCESS_PRIORITY.get(primary.access_state, 0)
    sec_p = ACCESS_PRIORITY.get(secondary.access_state, 0)

    if sec_p > pri_p:
        primary.access_state = secondary.access_state
        primary.access_classification = secondary.access_classification
        primary.access_type = secondary.access_type
        primary.access_message = secondary.access_message
        primary.reader_type = secondary.reader_type
        primary.licensing = secondary.licensing

    primary.is_open_access = bool(primary.is_open_access or secondary.is_open_access)

    # 2. Reader / Embed URL
    if not primary.embed_url and secondary.embed_url:
        primary.embed_url = secondary.embed_url
        primary.can_embed = secondary.can_embed
    elif secondary.can_embed and not primary.can_embed:
        primary.embed_url = secondary.embed_url
        primary.can_embed = True

    if not primary.reader_url and secondary.reader_url:
        primary.reader_url = secondary.reader_url

    if not primary.external_search_url and secondary.external_search_url:
        primary.external_search_url = secondary.external_search_url

    # 3. Download URLs (PDF & EPUB)
    if not primary.download_url and secondary.download_url:
        primary.download_url = secondary.download_url
    if not primary.pdf_url and (secondary.pdf_url or (secondary.download_url and ".pdf" in (secondary.download_url or "").lower())):
        primary.pdf_url = secondary.pdf_url or secondary.download_url
    if not primary.epub_url and (secondary.epub_url or (secondary.download_url and ".epub" in (secondary.download_url or "").lower())):
        primary.epub_url = secondary.epub_url or secondary.download_url
    if not primary.format and secondary.format:
        primary.format = secondary.format

    # 4. Thumbnail & Description
    if not primary.thumbnail_url and secondary.thumbnail_url:
        primary.thumbnail_url = secondary.thumbnail_url
    if (not primary.description or len(primary.description) < 40) and secondary.description:
        primary.description = secondary.description

    # 5. Merged ISBNs
    all_isbns = list(dict.fromkeys(primary.isbns + secondary.isbns))
    primary.isbns = all_isbns[:5]
    if not primary.isbn_10 and secondary.isbn_10:
        primary.isbn_10 = secondary.isbn_10
    if not primary.isbn_13 and secondary.isbn_13:
        primary.isbn_13 = secondary.isbn_13

    return primary


async def _run_single_provider(
    provider_name: str,
    search_coro_fn,
    query: BookSearchQuery,
    limit: int
) -> Tuple[str, List[BookCandidate], ProviderStatus]:
    """Execute a single provider query with timing, caching, and circuit breaker protection."""
    start_time = time.perf_counter()

    # Check cache first
    cached_results = await search_cache.get(provider_name, query, limit)
    if cached_results is not None:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        p_status = ProviderStatus(
            provider_name=provider_name,
            status="SUCCESS" if cached_results else "NO_RESULTS",
            results_count=len(cached_results),
            message=f"Served {len(cached_results)} candidate(s) from query cache ({elapsed_ms}ms)." if cached_results else "Cached zero-results for query.",
            elapsed_ms=elapsed_ms,
            cached=True
        )
        return provider_name, cached_results, p_status

    # Check circuit breaker before sending network request
    breaker = get_circuit_breaker(provider_name)
    allowed, block_msg = await breaker.allow_request()
    if not allowed:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        p_status = ProviderStatus(
            provider_name=provider_name,
            status="CIRCUIT_OPEN",
            results_count=0,
            message=block_msg,
            elapsed_ms=elapsed_ms,
            cached=False
        )
        return provider_name, [], p_status

    try:
        async with PROVIDER_SEMAPHORE:
            results = await asyncio.wait_for(
                search_coro_fn(query, limit=limit),
                timeout=PROVIDER_TIMEOUT_SECONDS
            )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        await breaker.record_success()

        # Cache results
        await search_cache.set(provider_name, query, limit, results)

        p_status = ProviderStatus(
            provider_name=provider_name,
            status="SUCCESS" if results else "NO_RESULTS",
            results_count=len(results),
            message=f"Discovered {len(results)} candidate record(s) ({elapsed_ms}ms)." if results else f"No matching volumes found ({elapsed_ms}ms).",
            elapsed_ms=elapsed_ms,
            cached=False
        )
        return provider_name, results, p_status

    except asyncio.TimeoutError:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        await breaker.record_failure("Timeout")
        logger.warning(f"Provider '{provider_name}' timed out after {PROVIDER_TIMEOUT_SECONDS}s.")
        p_status = ProviderStatus(
            provider_name=provider_name,
            status="UNAVAILABLE",
            results_count=0,
            message=f"Query timed out after {PROVIDER_TIMEOUT_SECONDS}s; other sources returned.",
            elapsed_ms=elapsed_ms,
            cached=False
        )
        return provider_name, [], p_status

    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        msg = str(e)
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code == 429 or "RATE_LIMITED" in msg or "429" in msg or "rate limit" in msg.lower():
            st = "RATE_LIMITED"
            msg = f"{provider_name} reported HTTP 429 rate limit. Other active providers compiled."
        elif "CIRCUIT_OPEN" in msg:
            st = "CIRCUIT_OPEN"
        elif status_code in (503, 504) or "UNAVAILABLE" in msg:
            st = "UNAVAILABLE"
        else:
            st = "ERROR"

        logger.info(f"Provider '{provider_name}' outcome: {st} ({msg}) in {elapsed_ms}ms")
        p_status = ProviderStatus(
            provider_name=provider_name,
            status=st,
            results_count=0,
            message=msg,
            elapsed_ms=elapsed_ms,
            cached=False
        )
        return provider_name, [], p_status


async def aggregate_and_rank_candidates_with_status(
    query: BookSearchQuery,
    limit: int = 8,
    return_related: bool = False
) -> Any:
    """
    Search multiple metadata sources and authorized repositories concurrently,
    measure latency per provider, apply circuit breaking and caching,
    normalize and deduplicate editions, score 0-100 confidence,
    and persist results in SQLite.
    """
    search_id = f"srch_{uuid.uuid4().hex[:10]}"
    all_raw_candidates: List[BookCandidate] = []
    provider_statuses: List[ProviderStatus] = []

    # Decompose unified query string if title/author/isbn are missing
    if query.q and query.q.strip():
        dt, da, di = _decompose_query_string(query.q)
        if not query.title and dt:
            query.title = dt
        if not query.author and da:
            query.author = da
        if not query.isbn and di:
            query.isbn = di

    if query.use_mock_data:
        logger.info("Using mock candidates data as requested by query.")
        mocks = load_mock_candidates(query)
        all_raw_candidates.extend(mocks)
        provider_statuses.append(
            ProviderStatus(
                provider_name="Offline Mock Catalog",
                status="SUCCESS",
                results_count=len(mocks),
                message="Loaded reference candidate records from local verification dataset.",
                elapsed_ms=1.0,
                cached=True
            )
        )
    else:
        # Full suite of legitimate providers
        provider_tasks = [
            ("Open Library", search_open_library),
            ("Google Books", search_google_books),
            ("Internet Archive", search_internet_archive),
            ("Project Gutenberg", search_gutenberg_repository),
            ("OpenStax Open Textbooks", search_openstax),
            ("Authorized Web Discovery", search_authorized_web_discovery),
            ("Directory of Open Access Books (DOAB)", search_doab),
            ("Crossref Academic Registry", search_crossref),
        ]

        # Dispatch parallel bounded tasks
        coroutines = [
            _run_single_provider(name, fn, query, limit=limit)
            for name, fn in provider_tasks
        ]
        results_list = await asyncio.gather(*coroutines, return_exceptions=False)

        for provider_name, cands, status_obj in results_list:
            all_raw_candidates.extend(cands)
            provider_statuses.append(status_obj)

    # ==========================================================
    # Deduplicate identical editions while preserving distinct editions
    # ==========================================================
    # Group by: clean title + primary author surname + normalized edition + publication year
    edition_map: Dict[str, BookCandidate] = {}

    for cand in all_raw_candidates:
        clean_title = _clean_str(cand.title)
        surname = _extract_author_surname(cand.authors)
        ed_norm = _normalize_edition_string(cand.edition)
        year_str = str(cand.published_year or "")

        # Distinct edition key
        edition_key = f"{clean_title}::{surname}::{ed_norm}::{year_str}"

        # If ISBN is present, also check ISBN collision
        primary_isbn = _extract_primary_isbn(cand)
        if primary_isbn:
            isbn_key = f"isbn::{primary_isbn}"
            # Check if this ISBN was already mapped under another edition key
            matching_key = None
            for ek, existing in edition_map.items():
                if primary_isbn in [re.sub(r"[^0-9Xx]", "", i) for i in existing.isbns]:
                    matching_key = ek
                    break
            if matching_key:
                edition_key = matching_key

        if edition_key in edition_map:
            # Merge candidate records to keep best reader/download access
            edition_map[edition_key] = _merge_candidates(edition_map[edition_key], cand)
        else:
            edition_map[edition_key] = cand

    unique_candidates: List[BookCandidate] = []
    related_candidates: List[BookCandidate] = []

    for cand in edition_map.values():
        # Enforce whitelist domain guardrails
        cand = _enforce_domain_guardrails(cand)

        # Calculate explainable deterministic Python confidence score
        cand.confidence = calculate_confidence(query, cand)

        # Rule 5 & 7: Separate exact matches, alternate editions, related works, and unrelated records
        if cand.match_type == "UNRELATED":
            # Reject unrelated records from the primary result list
            continue
        elif cand.match_type == "RELATED_PUBLICATION":
            related_candidates.append(cand)
        else:
            unique_candidates.append(cand)

    # ==========================================================
    # Rank candidates: exact title/author first, then confidence score, then access state
    # ==========================================================
    target_clean = _clean_str(query.title or query.q or "")

    def ranking_key(c: BookCandidate):
        c_title_clean = _clean_str(c.title)
        is_exact = 1 if (target_clean and c_title_clean == target_clean) else 0

        # Access weight: authorized full-text and downloads ranked prominently
        access_bonus = 0.0
        if c.access_state == AccessState.AUTHORIZED_DOWNLOAD:
            access_bonus = 5.0
        elif c.access_state == AccessState.FULL_TEXT_ONLINE:
            access_bonus = 3.0

        score = c.confidence.total_score if c.confidence else 0.0
        approx_penalty = -20.0 if c.is_approximate_suggestion else 0.0

        return (is_exact, score + access_bonus + approx_penalty)

    unique_candidates.sort(key=ranking_key, reverse=True)
    shortlist = unique_candidates[:limit]
    related_candidates.sort(key=lambda c: c.confidence.total_score if c.confidence else 0.0, reverse=True)

    # Persist search request and candidates in SQLite (including related publications)
    try:
        repository.save_search(search_id, query, shortlist + related_candidates[:limit])
    except Exception as e:
        logger.error(f"Failed to persist search {search_id} to SQLite: {e}")

    if return_related:
        return shortlist, provider_statuses, related_candidates[:limit]
    return shortlist, provider_statuses


async def aggregate_and_rank_candidates(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """Backward-compatible helper returning shortlist of candidates."""
    candidates, _ = await aggregate_and_rank_candidates_with_status(query, limit=limit)
    return candidates
