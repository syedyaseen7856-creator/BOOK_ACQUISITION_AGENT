from app.routers.health import router as health_router
from app.routers.search import router as search_router
from app.routers.approval import router as approval_router
from app.routers.download_stub import router as download_router

__all__ = ["health_router", "search_router", "approval_router", "download_router"]
