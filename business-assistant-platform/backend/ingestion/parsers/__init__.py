"""
File: backend/ingestion/parsers/__init__.py
Purpose: Exposes parser utilities for supported ingestion file formats.
"""

from backend.ingestion.parsers.base import ParsedDocument
from backend.ingestion.parsers.factory import parse_uploaded_file

__all__ = ["ParsedDocument", "parse_uploaded_file"]

