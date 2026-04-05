"""
File: backend/ingestion/parsers/base.py
Purpose: Shared parser output contract for normalized ingestion processing.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedDocument:
    """
    Canonical parser output consumed by cleaners and persistence handlers.
    """

    document_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tabular_preview: list[dict[str, Any]] = field(default_factory=list)

