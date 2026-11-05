from fastapi import APIRouter
from app.config import settings
from app.services.approval_service import approval_service
from app.services.gemini_verifier import gemini_verifier

router = APIRouter(tags=["Health & System"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }


@router.get("/api/system-status")
async def system_status():
    approvals = approval_service.list_approvals()
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_flash_configured": gemini_verifier.is_available,
        "gemini_model": settings.GEMINI_MODEL,
        "search_provider": settings.SEARCH_PROVIDER,
        "allowed_domains": list(settings.allowed_domains_set),
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "total_approvals_count": len(approvals),
        "milestone": "Milestone 1 — Search, Ranking, Licensing & Approval Interface"
    }
