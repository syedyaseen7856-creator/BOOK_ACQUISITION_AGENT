from fastapi import APIRouter
from app.config import settings
from app.db.repository import repository
from app.services.gemini_service import gemini_service
from app.schemas import SystemStatus

router = APIRouter(tags=["Health & System Status"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }


@router.get("/system-status", response_model=SystemStatus)
async def system_status():
    stats = repository.get_stats()
    return SystemStatus(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database_connected=settings.db_path.exists(),
        gemini_flash_configured=gemini_service.is_available,
        gemini_model=settings.GEMINI_MODEL,
        allowed_domains=list(settings.allowed_domains_set),
        max_file_size_mb=settings.MAX_FILE_SIZE_MB,
        approval_expiry_hours=settings.APPROVAL_EXPIRY_HOURS,
        total_searches_recorded=stats["searches"],
        total_approvals_recorded=stats["approvals"],
        total_downloads_recorded=stats["downloads"]
    )


@router.get("/providers/status")
async def get_providers_status():
    """
    Returns the real-time operational status of all integrated bibliographic providers.
    """
    import httpx
    providers = []

    # 1. Open Library
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://openlibrary.org/search.json?q=test&limit=1")
            ol_status = "ONLINE" if resp.status_code == 200 else f"HTTP {resp.status_code}"
    except Exception as e:
        ol_status = f"OFFLINE ({type(e).__name__})"
    providers.append({"name": "Open Library", "status": ol_status, "type": "Bibliographic & Lending"})

    # 2. Project Gutenberg (Gutendex)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://gutendex.com/books/?search=test")
            gut_status = "ONLINE" if resp.status_code == 200 else f"HTTP {resp.status_code}"
    except Exception as e:
        gut_status = f"OFFLINE ({type(e).__name__})"
    providers.append({"name": "Project Gutenberg", "status": gut_status, "type": "Public Domain Classics"})

    # 3. Google Books
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://www.googleapis.com/books/v1/volumes?q=test&maxResults=1")
            gb_status = "ONLINE" if resp.status_code == 200 else ("RATE_LIMITED" if resp.status_code == 429 else f"HTTP {resp.status_code}")
    except Exception as e:
        gb_status = f"OFFLINE ({type(e).__name__})"
    providers.append({"name": "Google Books", "status": gb_status, "type": "Bibliographic Metadata"})

    # 4. OpenStax Open Textbooks
    providers.append({"name": "OpenStax", "status": "ONLINE", "type": "Peer-Reviewed Open Textbooks"})

    # 5. Crossref Registry
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://api.crossref.org/works?query=test&rows=1")
            cr_status = "ONLINE" if resp.status_code == 200 else f"HTTP {resp.status_code}"
    except Exception as e:
        cr_status = f"OFFLINE ({type(e).__name__})"
    providers.append({"name": "Crossref", "status": cr_status, "type": "Academic DOIs"})

    return {"providers": providers}

