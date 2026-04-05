"""
File: backend/ingestion/processors/__init__.py
Purpose: Exposes shared content-cleaning and chunking utilities for ingestion.
"""

from backend.ingestion.processors.cleaner import chunk_text, normalize_text

__all__ = ["normalize_text", "chunk_text"]

