from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.settings import settings
from .api import logs_router, incidents_router, health_router, ai_router, reports_router
from .database.session import engine
from .models import base

# Initialize database tables
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="SOC Security Log Analysis Assistant — local-first, AI-powered threat detection.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health_router,    prefix=f"{settings.API_V1_STR}/health",    tags=["Health"])
app.include_router(logs_router,      prefix=f"{settings.API_V1_STR}/logs",      tags=["Logs"])
app.include_router(incidents_router, prefix=f"{settings.API_V1_STR}/incidents", tags=["Incidents"])
app.include_router(ai_router,        prefix=f"{settings.API_V1_STR}/ai",        tags=["AI Copilot"])
app.include_router(reports_router,   prefix=f"{settings.API_V1_STR}/reports",   tags=["Reports"])

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Security Log Analysis Assistant API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
    }
