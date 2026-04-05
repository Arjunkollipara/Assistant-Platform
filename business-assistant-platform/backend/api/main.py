"""
File: backend/api/main.py
Purpose: FastAPI application entry point for Layer 1 ingestion workflows.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from backend.api.routers import ingestion_router, ml_router
from backend.core.config import get_settings
from backend.core.db import init_relational_database
from backend.core.storage import ensure_ingestion_buckets

settings = get_settings()
LAYER2_DASHBOARD_PATH = (
    Path(__file__).resolve().parent / "static" / "layer2_validation_dashboard.html"
)


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
        "Layer 1 and Layer 2 API for the AI-Powered Autonomous Business Assistant Platform. "
        "Provides ingestion, asynchronous model training, and prediction endpoints."
    ),
    lifespan=lifespan,
)

app.include_router(ingestion_router, prefix=settings.API_PREFIX)
app.include_router(ml_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """
    Return a basic descriptor so service startup can be verified quickly.
    """
    return {
        "service": settings.APP_NAME,
        "message": "Layer 1 + Layer 2 APIs are running.",
        "health_url": "/health",
        "ingestion_upload_url": f"{settings.API_PREFIX}/ingestion/upload",
        "ml_train_url": f"{settings.API_PREFIX}/ml/train",
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


@app.get("/layer2/dashboard", response_class=HTMLResponse, tags=["meta"])
def layer2_validation_dashboard() -> str:
    """
    Serve a lightweight dashboard to visualize Layer 2 evaluation outputs.
    """
    return LAYER2_DASHBOARD_PATH.read_text(encoding="utf-8")
