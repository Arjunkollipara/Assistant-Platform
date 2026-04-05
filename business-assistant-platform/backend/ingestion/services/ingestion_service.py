"""
File: backend/ingestion/services/ingestion_service.py
Purpose: Service-layer orchestration for upload validation, persistence, and task dispatch.
"""

import os
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.core.celery_app import celery_app
from backend.core.config import get_settings
from backend.core.models import IngestionDocument, IngestionJob, IngestionStatus
from backend.core.storage import (
    build_raw_object_key,
    ensure_ingestion_buckets,
    upload_bytes,
)

settings = get_settings()


def _extract_extension(filename: str) -> str:
    """
    Extract lowercase extension without leading dot.
    """
    return os.path.splitext(filename)[1].lower().lstrip(".")


def _validate_upload(filename: str, size_bytes: int) -> str:
    """
    Validate file extension and size before persistence.
    """
    extension = _extract_extension(filename)
    if extension not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise ValueError(f"Unsupported file extension '{extension}'. Allowed: {allowed}.")

    if size_bytes > settings.ingestion_max_file_size_bytes:
        raise ValueError(
            "Uploaded file exceeds size limit "
            f"({settings.INGESTION_MAX_FILE_SIZE_MB} MB)."
        )
    return extension


def create_ingestion_job(
    db_session: Session,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> dict[str, Any]:
    """
    Persist job metadata, upload raw artifact, and enqueue Celery processing task.
    """
    if not filename:
        raise ValueError("Filename must be provided.")
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    extension = _validate_upload(filename=filename, size_bytes=len(file_bytes))
    job_id = str(uuid4())
    raw_object_key = build_raw_object_key(job_id=job_id, filename=filename)

    ensure_ingestion_buckets()
    upload_bytes(
        bucket=settings.MINIO_BUCKET_RAW,
        object_key=raw_object_key,
        payload=file_bytes,
        content_type=content_type or "application/octet-stream",
    )

    job = IngestionJob(
        id=job_id,
        original_filename=filename,
        file_extension=extension,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(file_bytes),
        raw_object_key=raw_object_key,
        status=IngestionStatus.QUEUED,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    task_result = celery_app.send_task(
        "backend.ingestion.tasks.ingestion_tasks.process_ingestion_job",
        kwargs={"job_id": job_id},
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "task_id": task_result.id,
        "filename": job.original_filename,
        "file_extension": job.file_extension,
        "size_bytes": job.size_bytes,
    }


def fetch_job(db_session: Session, job_id: str) -> IngestionJob | None:
    """
    Fetch ingestion job by primary key.
    """
    return db_session.get(IngestionJob, job_id)


def fetch_document(db_session: Session, document_id: str) -> IngestionDocument | None:
    """
    Fetch processed document metadata by primary key.
    """
    return db_session.get(IngestionDocument, document_id)

