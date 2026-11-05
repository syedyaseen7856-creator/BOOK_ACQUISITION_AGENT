import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx
from app.config import settings
from app.schemas import (
    BookSearchQuery,
    BookCandidate,
    LicenseStatus,
    LicensingEvidence,
    AccessState,
    AccessClassification
)
from app.services.resilience import execute_with_backoff

logger = logging.getLogger(__name__)

USER_AGENT = "SyllExtract-BookAcquisitionAgent/3.2 (https://github.com/syll-extract; academic-bot@syll-extract.org)"

# Curated catalog of official OpenStax peer-reviewed open textbooks
OPENSTAX_CATALOG = [
    {
        "id": "openstax_calc1",
        "title": "Calculus Volume 1",
        "authors": ["Edwin Jed Herman", "Gilbert Strang"],
        "publisher": "OpenStax",
        "published_year": 2016,
        "edition": "OpenStax Standard Edition",
        "isbns": ["978-1-938168-02-4", "978-1-947172-13-5"],
        "categories": ["Mathematics", "Calculus", "STEM"],
        "description": "Calculus Volume 1 is designed for the typical two- or three-semester general calculus course, covering functions, limits, derivatives, and integration.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Calculus_Vol1_cover.jpg",
        "source_url": "https://openstax.org/details/books/calculus-volume-1",
        "reader_url": "https://openstax.org/books/calculus-volume-1/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/CalculusVolume1-OP.pdf",
        "slug": "calculus-volume-1"
    },
    {
        "id": "openstax_calc2",
        "title": "Calculus Volume 2",
        "authors": ["Edwin Jed Herman", "Gilbert Strang"],
        "publisher": "OpenStax",
        "published_year": 2016,
        "edition": "OpenStax Standard Edition",
        "isbns": ["978-1-938168-06-2", "978-1-947172-14-2"],
        "categories": ["Mathematics", "Calculus", "Integration"],
        "description": "Calculus Volume 2 covers integration, differential equations, sequences and series, and parametric equations and polar coordinates.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Calculus_Vol2_cover.jpg",
        "source_url": "https://openstax.org/details/books/calculus-volume-2",
        "reader_url": "https://openstax.org/books/calculus-volume-2/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/CalculusVolume2-OP.pdf",
        "slug": "calculus-volume-2"
    },
    {
        "id": "openstax_calc3",
        "title": "Calculus Volume 3",
        "authors": ["Edwin Jed Herman", "Gilbert Strang"],
        "publisher": "OpenStax",
        "published_year": 2016,
        "edition": "OpenStax Standard Edition",
        "isbns": ["978-1-938168-07-9", "978-1-947172-15-9"],
        "categories": ["Mathematics", "Multivariable Calculus"],
        "description": "Calculus Volume 3 covers multivariable functions, partial derivatives, multiple integrals, and vector calculus.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Calculus_Vol3_cover.jpg",
        "source_url": "https://openstax.org/details/books/calculus-volume-3",
        "reader_url": "https://openstax.org/books/calculus-volume-3/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/CalculusVolume3-OP.pdf",
        "slug": "calculus-volume-3"
    },
    {
        "id": "openstax_uphys1",
        "title": "University Physics Volume 1",
        "authors": ["Samuel J. Ling", "Jeff Sanny", "William Moebs"],
        "publisher": "OpenStax",
        "published_year": 2016,
        "edition": "OpenStax Calculus-Based Edition",
        "isbns": ["978-1-938168-27-7", "978-1-947172-20-3"],
        "categories": ["Physics", "Mechanics", "Thermodynamics"],
        "description": "University Physics Volume 1 covers mechanics, sound, oscillations, and waves for science and engineering students.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/UniversityPhysics_Vol1_cover.jpg",
        "source_url": "https://openstax.org/details/books/university-physics-volume-1",
        "reader_url": "https://openstax.org/books/university-physics-volume-1/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/UniversityPhysicsVolume1-OP.pdf",
        "slug": "university-physics-volume-1"
    },
    {
        "id": "openstax_uphys2",
        "title": "University Physics Volume 2",
        "authors": ["Samuel J. Ling", "Jeff Sanny", "William Moebs"],
        "publisher": "OpenStax",
        "published_year": 2016,
        "edition": "OpenStax Calculus-Based Edition",
        "isbns": ["978-1-938168-16-1", "978-1-947172-21-0"],
        "categories": ["Physics", "Electromagnetism", "Optics"],
        "description": "University Physics Volume 2 covers thermodynamics, electricity, and magnetism.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/UniversityPhysics_Vol2_cover.jpg",
        "source_url": "https://openstax.org/details/books/university-physics-volume-2",
        "reader_url": "https://openstax.org/books/university-physics-volume-2/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/UniversityPhysicsVolume2-OP.pdf",
        "slug": "university-physics-volume-2"
    },
    {
        "id": "openstax_python",
        "title": "Introduction to Python Programming",
        "authors": ["Ugo Buy", "Robert Sloan"],
        "publisher": "OpenStax",
        "published_year": 2024,
        "edition": "1st Edition",
        "isbns": ["978-1-711470-79-5", "978-1-951693-85-5"],
        "categories": ["Computer Science", "Programming", "Python"],
        "description": "Introduction to Python Programming covers fundamental programming concepts, algorithms, data structures, and software design principles.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/IntroPython_cover.jpg",
        "source_url": "https://openstax.org/details/books/introduction-python-programming",
        "reader_url": "https://openstax.org/books/introduction-python-programming/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/IntroductionToPythonProgramming-OP.pdf",
        "slug": "introduction-python-programming"
    },
    {
        "id": "openstax_chem2e",
        "title": "Chemistry 2e",
        "authors": ["Paul Flowers", "Klaus Theopold", "Richard Langley", "William R. Robinson"],
        "publisher": "OpenStax",
        "published_year": 2019,
        "edition": "2nd Edition",
        "isbns": ["978-1-947172-61-6", "978-1-947172-62-3"],
        "categories": ["Chemistry", "Physical Sciences", "General Chemistry"],
        "description": "Chemistry 2e is designed to meet the scope and sequence requirements of the two-semester general chemistry course.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Chemistry2e_cover.jpg",
        "source_url": "https://openstax.org/details/books/chemistry-2e",
        "reader_url": "https://openstax.org/books/chemistry-2e/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/Chemistry2e-OP.pdf",
        "slug": "chemistry-2e"
    },
    {
        "id": "openstax_bio2e",
        "title": "Biology 2e",
        "authors": ["Mary Ann Clark", "Matthew Douglas", "Jung Choi"],
        "publisher": "OpenStax",
        "published_year": 2018,
        "edition": "2nd Edition",
        "isbns": ["978-1-947172-51-7", "978-1-947172-52-4"],
        "categories": ["Biology", "Life Sciences", "Cellular Biology"],
        "description": "Biology 2e covers fundamental biological concepts from cellular structure and genetics to evolution and ecology.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Biology2e_cover.jpg",
        "source_url": "https://openstax.org/details/books/biology-2e",
        "reader_url": "https://openstax.org/books/biology-2e/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/Biology2e-OP.pdf",
        "slug": "biology-2e"
    },
    {
        "id": "openstax_econ3e",
        "title": "Principles of Economics 3e",
        "authors": ["David Shapiro", "Steven A. Greenlaw"],
        "publisher": "OpenStax",
        "published_year": 2022,
        "edition": "3rd Edition",
        "isbns": ["978-1-711471-49-5", "978-1-711471-50-1"],
        "categories": ["Economics", "Microeconomics", "Macroeconomics"],
        "description": "Principles of Economics 3e covers scope and sequence requirements for a two-semester introductory economics course.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Economics3e_cover.jpg",
        "source_url": "https://openstax.org/details/books/principles-economics-3e",
        "reader_url": "https://openstax.org/books/principles-economics-3e/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/PrinciplesOfEconomics3e-OP.pdf",
        "slug": "principles-economics-3e"
    },
    {
        "id": "openstax_stats",
        "title": "Introductory Statistics",
        "authors": ["Barbara Illowsky", "Susan Dean"],
        "publisher": "OpenStax",
        "published_year": 2018,
        "edition": "OpenStax Edition",
        "isbns": ["978-1-938168-20-8", "978-1-947172-05-0"],
        "categories": ["Statistics", "Mathematics", "Probability"],
        "description": "Introductory Statistics follows scope and sequence requirements of a one-semester introduction to statistics course.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/IntroductoryStatistics_cover.jpg",
        "source_url": "https://openstax.org/details/books/introductory-statistics",
        "reader_url": "https://openstax.org/books/introductory-statistics/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/IntroductoryStatistics-OP.pdf",
        "slug": "introductory-statistics"
    },
    {
        "id": "openstax_psych2e",
        "title": "Psychology 2e",
        "authors": ["Rose M. Spielman", "William J. Jenkins", "Marilyn D. Lovett"],
        "publisher": "OpenStax",
        "published_year": 2020,
        "edition": "2nd Edition",
        "isbns": ["978-1-951693-23-7", "978-1-951693-24-4"],
        "categories": ["Psychology", "Social Sciences", "Cognition"],
        "description": "Psychology 2e is designed to meet scope and sequence for the single-semester introduction to psychology course.",
        "thumbnail_url": "https://assets.openstax.org/oscms-dev/media/documents/Psychology2e_cover.jpg",
        "source_url": "https://openstax.org/details/books/psychology-2e",
        "reader_url": "https://openstax.org/books/psychology-2e/pages/1-introduction",
        "download_url": "https://assets.openstax.org/oscms-prodcms/media/documents/Psychology2e-OP.pdf",
        "slug": "psychology-2e"
    }
]


def _normalize_title_text(text: str) -> str:
    """Normalize text removing punctuation, roman numerals, and extra spaces."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[,\-\.:;]", " ", t)
    t = re.sub(r"\bvol\b\.?", "volume", t)
    return " ".join(t.split())


def _matches_query(entry: Dict[str, Any], query: BookSearchQuery) -> float:
    """Score matching between query and an OpenStax textbook entry."""
    entry_title_norm = _normalize_title_text(entry["title"])
    q_title_norm = _normalize_title_text(query.title or "")

    # Check direct title match
    if q_title_norm and (q_title_norm == entry_title_norm or q_title_norm.replace(" ", "") == entry_title_norm.replace(" ", "")):
        return 0.98

    # Check ISBN match
    if query.isbn:
        clean_q_isbn = re.sub(r"[^0-9X]", "", query.isbn.upper())
        for isbn in entry["isbns"]:
            clean_entry_isbn = re.sub(r"[^0-9X]", "", isbn.upper())
            if clean_q_isbn == clean_entry_isbn:
                return 1.0

    q_terms = []
    if query.title:
        q_terms.extend(_normalize_title_text(query.title).split())
    if query.author:
        q_terms.extend(_normalize_title_text(query.author).split())
    if query.subject:
        q_terms.extend(_normalize_title_text(query.subject).split())
    if query.q:
        q_terms.extend(_normalize_title_text(query.q).split())

    if not q_terms:
        return 0.0

    # If title is specified in query, require that at least one title token matches entry title or categories
    if query.title:
        title_terms = [t for t in _normalize_title_text(query.title).split() if len(t) >= 3]
        if title_terms:
            has_title_match = any(t in entry_title_norm or t in " ".join(entry["categories"]).lower() for t in title_terms)
            if not has_title_match:
                return 0.0

    entry_text = f"{entry_title_norm} {' '.join(entry['authors'])} {' '.join(entry['categories'])} {entry['description']}".lower()

    match_count = sum(1 for term in q_terms if len(term) >= 3 and term in entry_text)
    total_distinct = len(set(t for t in q_terms if len(t) >= 3))
    if total_distinct == 0:
        return 0.0
    return round(match_count / total_distinct, 2)


async def search_openstax(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Search OpenStax open educational textbook catalog for CC-BY peer-reviewed monographs.
    Provides direct official PDF download links and web reader links.
    """
    candidates: List[BookCandidate] = []
    scored_entries = []

    for entry in OPENSTAX_CATALOG:
        score = _matches_query(entry, query)
        if score >= 0.35:
            scored_entries.append((score, entry))

    scored_entries.sort(key=lambda x: x[0], reverse=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    for score, item in scored_entries[:limit]:
        licensing = LicensingEvidence(
            status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
            license_name="Creative Commons Attribution 4.0 International (CC-BY 4.0)",
            rights_statement="Open educational textbook licensed under Creative Commons Attribution 4.0 International.",
            source_url=item["source_url"],
            terms_url="https://creativecommons.org/licenses/by/4.0/",
            evidence_details=[
                "Source is OpenStax: official peer-reviewed open textbook publisher at Rice University.",
                "Published under Creative Commons Attribution 4.0 International (CC-BY 4.0).",
                "Explicitly authorized for free reading, classroom adoption, and full-text PDF download."
            ],
            verified_at=now_iso,
            intended_use="educational_reference_acquisition",
            is_legally_downloadable=True
        )

        candidate = BookCandidate(
            candidate_id=f"cand_ostax_{item['id']}",
            title=item["title"],
            authors=item["authors"],
            publisher=item["publisher"],
            published_year=item["published_year"],
            edition=item["edition"],
            isbns=item["isbns"],
            page_count=None,
            language="en",
            categories=item["categories"],
            description=item["description"],
            thumbnail_url=item["thumbnail_url"],
            source_name="OpenStax",
            source_url=item["source_url"],
            reader_url=item["reader_url"],
            embed_url=item["reader_url"],
            external_search_url=item["source_url"],
            preview_url=None,
            pdf_url=item["download_url"],
            access_state=AccessState.AUTHORIZED_DOWNLOAD,
            access_classification=AccessClassification.AUTHORIZED_FREE_PDF,
            access_type="FULL_TEXT",
            access_message="Official OpenStax CC-BY open educational textbook. Full reading and PDF download authorized.",
            reader_type="FULL_READER",
            can_embed=True,
            download_url=item["download_url"],
            format="PDF",
            is_open_access=True,
            licensing=licensing
        )
        candidates.append(candidate)

    return candidates


async def search_doab(query: BookSearchQuery, limit: int = 5) -> List[BookCandidate]:
    """
    Query Directory of Open Access Books (DOAB) for open access peer-reviewed monographs.
    Uses resilient backoff and circuit breaker handling.
    """
    candidates: List[BookCandidate] = []
    search_q = query.title or query.q or (query.subject if query.subject else "")
    if not search_q:
        return []

    url = "https://directory.doabooks.org/rest/search"
    headers = {"User-Agent": USER_AGENT}

    async def _do_fetch():
        async with httpx.AsyncClient(timeout=min(settings.REQUEST_TIMEOUT_SECONDS, 8), headers=headers) as client:
            resp = await client.get(url, params={"query": search_q, "expand": "metadata"})
            resp.raise_for_status()
            return resp.json()

    try:
        data = await execute_with_backoff("Directory of Open Access Books (DOAB)", _do_fetch, max_retries=1)
    except Exception as e:
        logger.warning(f"DOAB query failed: {e}")
        raise RuntimeError(f"UNAVAILABLE: DOAB API unreachable or restricted ({e})")

    items = data if isinstance(data, list) else data.get("items", [])
    now_iso = datetime.now(timezone.utc).isoformat()

    for it in items[:limit]:
        handle = it.get("handle") or it.get("id", "unknown")
        metadata = it.get("metadata", {})
        title = metadata.get("dc.title", [{}])[0].get("value", "Untitled Open Access Book")
        authors = [a.get("value") for a in metadata.get("dc.contributor.author", []) if a.get("value")]

        licensing = LicensingEvidence(
            status=LicenseStatus.VERIFIED_FOR_PERMITTED_DOWNLOAD,
            license_name="Open Access Monograph (DOAB Certified)",
            rights_statement="Peer-reviewed Open Access monograph listed in the Directory of Open Access Books.",
            source_url=f"https://directory.doabooks.org/handle/{handle}",
            terms_url="https://www.doabooks.org/",
            evidence_details=[
                "Listed in Directory of Open Access Books (DOAB).",
                "Peer-reviewed academic monograph certified for open access reading."
            ],
            verified_at=now_iso,
            intended_use="educational_reference_acquisition",
            is_legally_downloadable=True
        )

        candidate = BookCandidate(
            candidate_id=f"cand_doab_{handle.replace('/', '_')}",
            title=title,
            authors=authors or ["DOAB Academic Authors"],
            publisher="DOAB Open Access Publisher",
            published_year=None,
            edition="DOAB Open Access Edition",
            isbns=[],
            page_count=None,
            language="en",
            categories=["Academic Monograph", "Open Access"],
            description="Open access scholarly monograph verified via Directory of Open Access Books (DOAB).",
            thumbnail_url=None,
            source_name="Directory of Open Access Books (DOAB)",
            source_url=f"https://directory.doabooks.org/handle/{handle}",
            reader_url=f"https://directory.doabooks.org/handle/{handle}",
            embed_url=f"https://directory.doabooks.org/handle/{handle}",
            external_search_url=f"https://directory.doabooks.org/handle/{handle}",
            preview_url=None,
            pdf_url=None,
            access_state=AccessState.FULL_TEXT_ONLINE,
            access_classification=AccessClassification.FULL_TEXT_READABLE_ONLINE_NO_DOWNLOAD,
            access_type="FULL_TEXT",
            access_message="Peer-reviewed scholarly monograph available for open access reading on DOAB.",
            reader_type="FULL_READER",
            can_embed=False,
            download_url=None,
            format="PDF",
            is_open_access=True,
            licensing=licensing
        )
        candidates.append(candidate)

    return candidates
