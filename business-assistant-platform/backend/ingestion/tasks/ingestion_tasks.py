"""
File: backend/ingestion/tasks/ingestion_tasks.py
Purpose: Celery task pipeline for asynchronous file parsing, cleaning, and persistence.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from backend.core.celery_app import celery_app
from backend.core.config import get_settings
from backend.core.db import SessionLocal, init_relational_database
from backend.core.models import IngestionDocument, IngestionJob, IngestionStatus
from backend.core.mongo import get_ingestion_chunk_collection
from backend.core.storage import (
    build_processed_object_key,
    download_bytes,
    ensure_ingestion_buckets,
    upload_json,
)
from backend.ingestion.parsers import parse_uploaded_file
from backend.ingestion.processors import chunk_text, normalize_text

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="backend.ingestion.tasks.ingestion_tasks.process_ingestion_job",
)
def process_ingestion_job(self, job_id: str) -> dict[str, object]:
    """
    Execute the full ingestion workflow for one uploaded file.
    """
    init_relational_database()
    ensure_ingestion_buckets()

    db_session = SessionLocal()
    try:
        job = db_session.get(IngestionJob, job_id)
        if not job:
            raise ValueError(f"Ingestion job '{job_id}' was not found.")

        job.status = IngestionStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        job.error_message = None
        db_session.commit()

        raw_file_bytes = download_bytes(
            bucket=settings.MINIO_BUCKET_RAW,
            object_key=job.raw_object_key,
        )
        parsed_document = parse_uploaded_file(job.file_extension, raw_file_bytes)
        cleaned_text = normalize_text(parsed_document.text)
        chunks = chunk_text(
            text=cleaned_text,
            chunk_size=settings.INGESTION_CHUNK_SIZE,
            overlap=settings.INGESTION_CHUNK_OVERLAP,
            max_chunks=settings.INGESTION_MAX_CHUNKS,
        )

        processed_object_key = build_processed_object_key(
            job_id=job.id,
            filename=job.original_filename,
        )

        processed_payload = {
            "job_id": job.id,
            "original_filename": job.original_filename,
            "document_type": parsed_document.document_type,
            "cleaned_text": cleaned_text,
            "chunk_count": len(chunks),
            "chunks": [
                {"chunk_index": index, "text": chunk}
                for index, chunk in enumerate(chunks)
            ],
            "tabular_preview": parsed_document.tabular_preview,
            "metadata": parsed_document.metadata,
            "processed_at": datetime.now(UTC).isoformat(),
        }
        upload_json(
            bucket=settings.MINIO_BUCKET_PROCESSED,
            object_key=processed_object_key,
            payload=processed_payload,
        )

        document_id = str(uuid4())
        document = IngestionDocument(
            id=document_id,
            job_id=job.id,
            original_filename=job.original_filename,
            document_type=parsed_document.document_type,
            processed_object_key=processed_object_key,
            chunk_count=len(chunks),
            char_count=len(cleaned_text),
            row_count=_metadata_int(parsed_document.metadata, "row_count"),
            column_count=_metadata_int(parsed_document.metadata, "column_count"),
            metadata_json=parsed_document.metadata,
        )
        db_session.add(document)

        _persist_chunks_to_mongo(
            document_id=document_id,
            job_id=job.id,
            chunks=chunks,
            document_type=parsed_document.document_type,
        )

        job.status = IngestionStatus.COMPLETED
        job.processed_object_key = processed_object_key
        job.completed_at = datetime.now(UTC)
        db_session.commit()

        logger.info(
            "Completed ingestion job %s with %s chunk(s).",
            job.id,
            len(chunks),
        )
        return {
            "job_id": job.id,
            "status": job.status,
            "document_id": document_id,
            "chunk_count": len(chunks),
            "processed_object_key": processed_object_key,
        }
    except Exception as exc:
        db_session.rollback()
        failed_job = db_session.get(IngestionJob, job_id)
        if failed_job:
            failed_job.status = IngestionStatus.FAILED
            failed_job.error_message = str(exc)[:2000]
            failed_job.completed_at = datetime.now(UTC)
            db_session.commit()

        logger.exception("Ingestion job %s failed: %s", job_id, exc)
        raise
    finally:
        db_session.close()


def _persist_chunks_to_mongo(
    document_id: str,
    job_id: str,
    chunks: list[str],
    document_type: str,
) -> None:
    """
    Persist chunked text in MongoDB for unstructured retrieval workflows.
    """
    collection = get_ingestion_chunk_collection()
    collection.delete_many({"document_id": document_id})

    chunk_documents = [
        {
            "document_id": document_id,
            "job_id": job_id,
            "chunk_index": index,
            "text": chunk,
            "document_type": document_type,
            "created_at": datetime.now(UTC),
        }
        for index, chunk in enumerate(chunks)
    ]
    if chunk_documents:
        collection.insert_many(chunk_documents)


def _metadata_int(metadata: dict, key: str) -> int | None:
    """
    Safely read integer-like values from parser metadata dictionaries.
    """
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

