"""
File: backend/ml/tasks/training_tasks.py
Purpose: Celery task pipeline for asynchronous model training and artifact persistence.
"""

import io
import logging
import pickle
from datetime import UTC, datetime
from uuid import uuid4

import mlflow
import pandas as pd

from backend.core.celery_app import celery_app
from backend.core.config import get_settings
from backend.core.db import SessionLocal, init_relational_database
from backend.core.models import IngestionJob, MLTrainingJob, MLTrainingStatus
from backend.core.storage import (
    build_model_object_key,
    download_bytes,
    ensure_ingestion_buckets,
    upload_bytes,
)
from backend.ml.services.training_pipeline import train_tabular_model

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    name="backend.ml.tasks.training_tasks.process_training_job",
)
def process_training_job(self, training_job_id: str) -> dict[str, object]:
    """
    Execute end-to-end training workflow for one asynchronous ML training request.
    """
    init_relational_database()
    ensure_ingestion_buckets()

    db_session = SessionLocal()
    try:
        training_job = db_session.get(MLTrainingJob, training_job_id)
        if not training_job:
            raise ValueError(f"Training job '{training_job_id}' was not found.")

        training_job.status = MLTrainingStatus.PROCESSING
        training_job.started_at = datetime.now(UTC)
        training_job.error_message = None
        db_session.commit()

        ingestion_job = db_session.get(IngestionJob, training_job.ingestion_job_id)
        if not ingestion_job:
            raise ValueError(
                f"Ingestion job '{training_job.ingestion_job_id}' was not found."
            )
        if ingestion_job.file_extension != "csv":
            raise ValueError("Layer 2 currently supports CSV datasets only.")

        dataset_bytes = download_bytes(
            bucket=settings.MINIO_BUCKET_RAW,
            object_key=ingestion_job.raw_object_key,
        )
        dataframe = pd.read_csv(io.BytesIO(dataset_bytes))

        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run(run_name=f"training_{training_job.id}") as run:
            mlflow.log_params(
                {
                    "training_job_id": training_job.id,
                    "ingestion_job_id": training_job.ingestion_job_id,
                    "target_column": training_job.target_column,
                    "requested_task_type": training_job.requested_task_type,
                    "requested_algorithm": training_job.algorithm,
                    "dataset_rows": int(len(dataframe)),
                    "dataset_columns": int(len(dataframe.columns)),
                }
            )

            artifacts = train_tabular_model(
                dataframe=dataframe,
                target_column=training_job.target_column,
                requested_task_type=training_job.requested_task_type,
                algorithm=training_job.algorithm,
            )

            mlflow.log_params(
                {
                    "resolved_task_type": artifacts.task_type,
                    "resolved_algorithm": artifacts.algorithm,
                    "feature_count": len(artifacts.feature_columns),
                }
            )
            mlflow.log_metrics(artifacts.metrics)
            mlflow.log_dict(
                {
                    "feature_columns": artifacts.feature_columns,
                    "class_labels": artifacts.class_labels,
                },
                artifact_file="training_metadata.json",
            )
            # Model binaries are stored in MinIO for serving; MLflow tracks params/metrics.

            model_id = str(uuid4())
            model_object_key = build_model_object_key(
                training_job_id=training_job.id,
                algorithm=artifacts.algorithm,
            )

            model_bundle = {
                "model_id": model_id,
                "task_type": artifacts.task_type,
                "algorithm": artifacts.algorithm,
                "target_column": training_job.target_column,
                "feature_columns": artifacts.feature_columns,
                "class_labels": artifacts.class_labels,
                "metrics": artifacts.metrics,
                "label_encoder": artifacts.label_encoder,
                "pipeline": artifacts.pipeline,
                "created_at": datetime.now(UTC).isoformat(),
            }

            # Serialized model bundle is generated internally and used only by trusted services.
            serialized_bundle = pickle.dumps(model_bundle)
            upload_bytes(
                bucket=settings.MINIO_BUCKET_MODELS,
                object_key=model_object_key,
                payload=serialized_bundle,
                content_type="application/octet-stream",
            )

            training_job.model_id = model_id
            training_job.task_type = artifacts.task_type
            training_job.algorithm = artifacts.algorithm
            training_job.status = MLTrainingStatus.COMPLETED
            training_job.model_object_key = model_object_key
            training_job.mlflow_experiment_name = settings.MLFLOW_EXPERIMENT_NAME
            training_job.mlflow_run_id = run.info.run_id
            training_job.metrics_json = artifacts.metrics
            training_job.feature_columns = artifacts.feature_columns
            training_job.class_labels = artifacts.class_labels
            training_job.row_count = artifacts.row_count
            training_job.completed_at = datetime.now(UTC)
            db_session.commit()

            logger.info(
                "Completed training job %s with model_id %s.",
                training_job.id,
                model_id,
            )
            return {
                "training_job_id": training_job.id,
                "model_id": model_id,
                "status": training_job.status,
                "task_type": training_job.task_type,
                "algorithm": training_job.algorithm,
                "metrics": training_job.metrics_json,
            }
    except Exception as exc:
        db_session.rollback()
        failed_job = db_session.get(MLTrainingJob, training_job_id)
        if failed_job:
            failed_job.status = MLTrainingStatus.FAILED
            failed_job.error_message = str(exc)[:2000]
            failed_job.completed_at = datetime.now(UTC)
            db_session.commit()

        logger.exception("Training job %s failed: %s", training_job_id, exc)
        raise
    finally:
        db_session.close()
