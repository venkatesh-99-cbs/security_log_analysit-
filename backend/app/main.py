from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.settings import settings
from .api import logs, incidents, health
from .database.session import engine
from .models import base

# Initialize database
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include Routers
app.include_router(logs.router, prefix=f"{settings.API_V1_STR}/logs", tags=["logs"])
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["incidents"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])

@app.get("/")
def root():
    return {"message": "Welcome to Security Log Analysis Assistant API"}
