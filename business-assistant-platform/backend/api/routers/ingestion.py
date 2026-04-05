"""
File: backend/api/routers/ingestion.py
Purpose: Layer 1 HTTP routes for upload, job tracking, and document metadata access.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.api.schemas.ingestion import (
    IngestionDocumentResponse,
    IngestionJobResponse,
    IngestionUploadResponse,
)
from backend.core.db import get_db_session
from backend.ingestion.services import create_ingestion_job, fetch_document, fetch_job

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post(
    "/upload",
    response_model=IngestionUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_file_for_ingestion(
    file: UploadFile = File(...),
    db_session: Session = Depends(get_db_session),
) -> IngestionUploadResponse:
    """
    Accept file uploads and enqueue asynchronous ingestion processing.
    """
    file_bytes = await file.read()

    try:
        payload = create_ingestion_job(
            db_session=db_session,
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ingestion job.",
        ) from exc

    return IngestionUploadResponse(**payload)


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
def get_ingestion_job(
    job_id: str,
    db_session: Session = Depends(get_db_session),
) -> IngestionJobResponse:
    """
    Retrieve ingestion job status and associated processed document IDs.
    """
    job = fetch_job(db_session, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job '{job_id}' was not found.",
        )

    document_ids = [document.id for document in job.documents]
    return IngestionJobResponse(
        job_id=job.id,
        status=job.status,
        original_filename=job.original_filename,
        file_extension=job.file_extension,
        size_bytes=job.size_bytes,
        raw_object_key=job.raw_object_key,
        processed_object_key=job.processed_object_key,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        document_ids=document_ids,
    )


@router.get("/documents/{document_id}", response_model=IngestionDocumentResponse)
def get_ingestion_document(
    document_id: str,
    db_session: Session = Depends(get_db_session),
) -> IngestionDocumentResponse:
    """
    Retrieve processed document metadata persisted after ingestion.
    """
    document = fetch_document(db_session, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion document '{document_id}' was not found.",
        )

    return IngestionDocumentResponse(
        document_id=document.id,
        job_id=document.job_id,
        original_filename=document.original_filename,
        document_type=document.document_type,
        processed_object_key=document.processed_object_key,
        chunk_count=document.chunk_count,
        char_count=document.char_count,
        row_count=document.row_count,
        column_count=document.column_count,
        metadata_json=document.metadata_json,
        created_at=document.created_at,
    )

