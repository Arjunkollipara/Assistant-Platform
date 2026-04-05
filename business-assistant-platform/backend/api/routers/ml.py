"""
File: backend/api/routers/ml.py
Purpose: Layer 2 HTTP routes for asynchronous model training and prediction.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.schemas.ml import (
    MLEvaluateRequest,
    MLEvaluateResponse,
    MLPredictRequest,
    MLPredictResponse,
    MLTrainRequest,
    MLTrainResponse,
    MLTrainingJobResponse,
)
from backend.core.db import get_db_session
from backend.ml.services import (
    create_training_job,
    evaluate_model_on_ingestion_job,
    fetch_training_job,
    predict_with_model,
)

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post(
    "/train",
    response_model=MLTrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_model_training_job(
    payload: MLTrainRequest,
    db_session: Session = Depends(get_db_session),
) -> MLTrainResponse:
    """
    Create asynchronous training job from a completed CSV ingestion dataset.
    """
    try:
        response_payload = create_training_job(
            db_session=db_session,
            ingestion_job_id=payload.ingestion_job_id,
            target_column=payload.target_column,
            task_type=payload.task_type,
            algorithm=payload.algorithm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create training job.",
        ) from exc

    return MLTrainResponse(**response_payload)


@router.get("/jobs/{training_job_id}", response_model=MLTrainingJobResponse)
def get_training_job_status(
    training_job_id: str,
    db_session: Session = Depends(get_db_session),
) -> MLTrainingJobResponse:
    """
    Retrieve training-job status and resulting model metadata.
    """
    training_job = fetch_training_job(db_session=db_session, training_job_id=training_job_id)
    if not training_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job '{training_job_id}' was not found.",
        )

    return MLTrainingJobResponse(
        training_job_id=training_job.id,
        model_id=training_job.model_id,
        ingestion_job_id=training_job.ingestion_job_id,
        status=training_job.status,
        target_column=training_job.target_column,
        requested_task_type=training_job.requested_task_type,
        task_type=training_job.task_type,
        algorithm=training_job.algorithm,
        metrics_json=training_job.metrics_json,
        feature_columns=training_job.feature_columns,
        class_labels=training_job.class_labels,
        row_count=training_job.row_count,
        model_object_key=training_job.model_object_key,
        mlflow_experiment_name=training_job.mlflow_experiment_name,
        mlflow_run_id=training_job.mlflow_run_id,
        error_message=training_job.error_message,
        created_at=training_job.created_at,
        started_at=training_job.started_at,
        completed_at=training_job.completed_at,
    )


@router.post("/predict", response_model=MLPredictResponse)
def predict_from_trained_model(
    payload: MLPredictRequest,
    db_session: Session = Depends(get_db_session),
) -> MLPredictResponse:
    """
    Run batch inference against a previously trained model.
    """
    try:
        response_payload = predict_with_model(
            db_session=db_session,
            model_id=payload.model_id,
            rows=payload.rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run prediction.",
        ) from exc

    return MLPredictResponse(**response_payload)


@router.post("/evaluate", response_model=MLEvaluateResponse)
def evaluate_model_predictions(
    payload: MLEvaluateRequest,
    db_session: Session = Depends(get_db_session),
) -> MLEvaluateResponse:
    """
    Compare model predictions with actual labels from a CSV ingestion dataset.
    """
    try:
        response_payload = evaluate_model_on_ingestion_job(
            db_session=db_session,
            model_id=payload.model_id,
            ingestion_job_id=payload.ingestion_job_id,
            target_column=payload.target_column,
            max_rows=payload.max_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate model.",
        ) from exc

    return MLEvaluateResponse(**response_payload)
