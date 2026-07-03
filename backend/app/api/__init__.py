from .logs import router as logs_router
from .incidents import router as incidents_router
from .health import router as health_router
from .ai import router as ai_router
from .reports import router as reports_router

__all__ = ["logs_router", "incidents_router", "health_router", "ai_router", "reports_router"]
