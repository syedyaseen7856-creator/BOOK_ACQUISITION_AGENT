from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.candidates import router as candidates_router
from app.api.approvals import router as approvals_router
from app.api.downloads import router as downloads_router
from app.api.jobs import router as jobs_router
from app.api.syllabus import router as syllabus_router
from app.api.batches import router as batches_router
from app.api.alternatives import router as alternatives_router
from app.api.history import router as history_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(search_router)
api_router.include_router(candidates_router)
api_router.include_router(approvals_router)
api_router.include_router(downloads_router)
api_router.include_router(jobs_router)
api_router.include_router(syllabus_router)
api_router.include_router(batches_router)
api_router.include_router(alternatives_router)
api_router.include_router(history_router)

__all__ = ["api_router"]
