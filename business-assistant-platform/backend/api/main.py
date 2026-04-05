"""
File: backend/api/main.py
Purpose: FastAPI application entry point for Layer 1 ingestion workflows.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routers import ingestion_router
from backend.core.config import get_settings
from backend.core.db import init_relational_database
from backend.core.storage import ensure_ingestion_buckets

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Initialize baseline storage and relational tables during API startup.
    """
    init_relational_database()
    ensure_ingestion_buckets()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    description=(
        "Layer 1 API for the AI-Powered Autonomous Business Assistant Platform. "
        "Provides upload, asynchronous processing, and ingestion status endpoints."
    ),
    lifespan=lifespan,
)

app.include_router(ingestion_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """
    Return a basic descriptor so service startup can be verified quickly.
    """
    return {
        "service": settings.APP_NAME,
        "message": "Layer 1 ingestion API is running.",
        "health_url": "/health",
        "ingestion_upload_url": f"{settings.API_PREFIX}/ingestion/upload",
    }


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    """
    Return process-level health plus key dependency addresses.
    """
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "api_prefix": settings.API_PREFIX,
        "dependencies": {
            "postgres": f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}",
            "mongodb": f"{settings.MONGO_HOST}:{settings.MONGO_PORT}",
            "redis": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            "minio": settings.minio_endpoint,
            "qdrant": f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            "mlflow": settings.MLFLOW_TRACKING_URI,
        },
    }

