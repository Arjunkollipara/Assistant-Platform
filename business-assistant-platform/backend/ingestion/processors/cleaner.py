"""
File: backend/ingestion/processors/cleaner.py
Purpose: Text normalization and chunking utilities for parsed document content.
"""

import re


def normalize_text(text: str) -> str:
    """
    Normalize extracted text by removing null bytes and collapsing whitespace.
    """
    if not text:
        return ""
    without_null_bytes = text.replace("\x00", " ")
    collapsed_newlines = re.sub(r"\n{3,}", "\n\n", without_null_bytes)
    collapsed_spaces = re.sub(r"[ \t]{2,}", " ", collapsed_newlines)
    return collapsed_spaces.strip()


def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int,
    max_chunks: int,
) -> list[str]:
    """
    Split text into overlapping character-based chunks for downstream retrieval.
    """
    if not text:
        return []

    effective_chunk_size = max(1, chunk_size)
    effective_overlap = max(0, min(overlap, effective_chunk_size - 1))

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length and len(chunks) < max_chunks:
        end = min(text_length, start + effective_chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = end - effective_overlap

    return chunks

