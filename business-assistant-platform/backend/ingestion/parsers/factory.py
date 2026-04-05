"""
File: backend/ingestion/parsers/factory.py
Purpose: Parser router that selects the correct parser based on file extension.
"""

from backend.ingestion.parsers.base import ParsedDocument
from backend.ingestion.parsers.csv_parser import parse_csv
from backend.ingestion.parsers.docx_parser import parse_docx
from backend.ingestion.parsers.pdf_parser import parse_pdf


def parse_uploaded_file(file_extension: str, file_bytes: bytes) -> ParsedDocument:
    """
    Route file bytes to the parser mapped to the provided extension.
    """
    normalized_extension = file_extension.lower().lstrip(".")
    if normalized_extension == "csv":
        return parse_csv(file_bytes)
    if normalized_extension == "pdf":
        return parse_pdf(file_bytes)
    if normalized_extension == "docx":
        return parse_docx(file_bytes)
    raise ValueError(f"Unsupported file extension: {file_extension}")

