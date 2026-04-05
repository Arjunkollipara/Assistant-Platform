"""
File: backend/api/routers/__init__.py
Purpose: Router exports for API module composition.
"""

from backend.api.routers.ingestion import router as ingestion_router

__all__ = ["ingestion_router"]

