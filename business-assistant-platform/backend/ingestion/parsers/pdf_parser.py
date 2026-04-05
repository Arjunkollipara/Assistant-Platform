"""
File: backend/ingestion/parsers/pdf_parser.py
Purpose: PDF parser that extracts text from each page for downstream processing.
"""

import io

from pypdf import PdfReader

from backend.ingestion.parsers.base import ParsedDocument


def parse_pdf(file_bytes: bytes) -> ParsedDocument:
    """
    Parse PDF bytes and concatenate extracted page text.
    """
    reader = PdfReader(io.BytesIO(file_bytes))

    page_texts: list[str] = []
    for page in reader.pages:
        page_texts.append(page.extract_text() or "")

    text = "\n".join(page_texts).strip()

    return ParsedDocument(
        document_type="pdf",
        text=text,
        metadata={
            "page_count": len(reader.pages),
            "char_count_raw": len(text),
        },
    )

