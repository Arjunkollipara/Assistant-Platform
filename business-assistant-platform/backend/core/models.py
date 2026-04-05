"""
File: backend/core/models.py
Purpose: SQLAlchemy ORM models for Layer 1 ingestion job and document metadata.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.db import Base


class IngestionStatus(StrEnum):
    """
    Standard lifecycle states for ingestion jobs and documents.
    """

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(Base):
    """
    Tracks one uploaded file from enqueue to final processing outcome.
    """

    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    processed_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=IngestionStatus.QUEUED, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    documents: Mapped[list["IngestionDocument"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    training_jobs: Mapped[list["MLTrainingJob"]] = relationship(
        back_populates="ingestion_job",
        cascade="all, delete-orphan",
    )


class IngestionDocument(Base):
    """
    Stores canonical processed document metadata generated from one ingestion job.
    """

    __tablename__ = "ingestion_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ingestion_jobs.id"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)
    processed_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    job: Mapped[IngestionJob] = relationship(back_populates="documents")


class MLTrainingStatus(StrEnum):
    """
    Standard lifecycle states for asynchronous model-training jobs.
    """

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MLTrainingJob(Base):
    """
    Tracks model-training requests and resulting model artifacts.
    """

    __tablename__ = "ml_training_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    model_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )
    ingestion_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ingestion_jobs.id"), nullable=False, index=True
    )
    target_column: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_task_type: Mapped[str] = mapped_column(
        String(20), default="auto", nullable=False
    )
    task_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=MLTrainingStatus.QUEUED, nullable=False
    )
    model_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mlflow_experiment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    feature_columns: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    class_labels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ingestion_job: Mapped[IngestionJob] = relationship(back_populates="training_jobs")
