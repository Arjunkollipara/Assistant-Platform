"""
File: backend/api/schemas/ingestion.py
Purpose: Pydantic contracts for Layer 1 ingestion API responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestionUploadResponse(BaseModel):
    """
    API response returned when a new ingestion job is accepted.
    """

    job_id: str = Field(description="Database identifier for the ingestion job.")
    status: str = Field(description="Current lifecycle state of the job.")
    task_id: str = Field(description="Celery task identifier for async tracking.")
    filename: str = Field(description="Original uploaded filename.")
    file_extension: str = Field(description="Normalized file extension.")
    size_bytes: int = Field(description="Raw uploaded file size in bytes.")


class IngestionJobResponse(BaseModel):
    """
    API response for job-level status checks.
    """

    job_id: str
    status: str
    original_filename: str
    file_extension: str
    size_bytes: int
    raw_object_key: str
    processed_object_key: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    document_ids: list[str]


class IngestionDocumentResponse(BaseModel):
    """
    API response for processed document metadata.
    """

    document_id: str
    job_id: str
    original_filename: str
    document_type: str
    processed_object_key: str
    chunk_count: int
    char_count: int
    row_count: int | None
    column_count: int | None
    metadata_json: dict[str, Any]
    created_at: datetime

