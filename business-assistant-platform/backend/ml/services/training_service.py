"""
File: backend/ml/services/training_service.py
Purpose: Service-layer orchestration for async model-training job creation and retrieval.
"""

from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.core.celery_app import celery_app
from backend.core.models import (
    IngestionJob,
    MLTrainingJob,
    MLTrainingStatus,
)
from backend.ml.services.training_pipeline import SUPPORTED_ALGORITHMS, SUPPORTED_TASK_TYPES


def create_training_job(
    db_session: Session,
    ingestion_job_id: str,
    target_column: str,
    task_type: str,
    algorithm: str,
) -> dict[str, Any]:
    """
    Validate request, persist training job record, and enqueue Celery training task.
    """
    ingestion_job = db_session.get(IngestionJob, ingestion_job_id)
    if not ingestion_job:
        raise ValueError(f"Ingestion job '{ingestion_job_id}' was not found.")
    if ingestion_job.file_extension != "csv":
        raise ValueError(
            "Layer 2 currently supports supervised training from CSV ingestion jobs."
        )
    if ingestion_job.status != "completed":
        raise ValueError(
            "Training can only start after ingestion job status becomes 'completed'."
        )
    if not target_column.strip():
        raise ValueError("Target column must be provided.")

    normalized_task_type = task_type.strip().lower()
    normalized_algorithm = algorithm.strip().lower()
    if normalized_task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(
            "Invalid task_type. Allowed values: auto, classification, regression."
        )
    if normalized_algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            "Invalid algorithm. Allowed values: auto, xgboost, random_forest, "
            "logistic_regression, linear_regression."
        )

    training_job = MLTrainingJob(
        id=str(uuid4()),
        ingestion_job_id=ingestion_job.id,
        target_column=target_column.strip(),
        requested_task_type=normalized_task_type,
        algorithm=normalized_algorithm,
        status=MLTrainingStatus.QUEUED,
    )
    db_session.add(training_job)
    db_session.commit()
    db_session.refresh(training_job)

    task_result = celery_app.send_task(
        "backend.ml.tasks.training_tasks.process_training_job",
        kwargs={"training_job_id": training_job.id},
    )

    return {
        "training_job_id": training_job.id,
        "status": training_job.status,
        "task_id": task_result.id,
        "ingestion_job_id": training_job.ingestion_job_id,
        "target_column": training_job.target_column,
        "requested_task_type": training_job.requested_task_type,
        "algorithm": training_job.algorithm,
    }


def fetch_training_job(db_session: Session, training_job_id: str) -> MLTrainingJob | None:
    """
    Fetch a model-training job by primary key.
    """
    return db_session.get(MLTrainingJob, training_job_id)


def fetch_training_job_by_model_id(
    db_session: Session, model_id: str
) -> MLTrainingJob | None:
    """
    Fetch the completed training job that produced the given model identifier.
    """
    return db_session.query(MLTrainingJob).filter(MLTrainingJob.model_id == model_id).first()

