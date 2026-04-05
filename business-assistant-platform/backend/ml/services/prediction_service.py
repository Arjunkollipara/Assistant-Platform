"""
File: backend/ml/services/prediction_service.py
Purpose: Inference utilities for loading trained model bundles and producing predictions.
"""

import pickle
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.models import MLTrainingStatus
from backend.core.storage import download_bytes
from backend.ml.services.training_service import fetch_training_job_by_model_id

settings = get_settings()


def predict_with_model(
    db_session: Session,
    model_id: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run inference using a previously trained model identified by model_id.
    """
    training_job = fetch_training_job_by_model_id(db_session=db_session, model_id=model_id)
    if not training_job:
        raise ValueError(f"Model '{model_id}' was not found.")
    if training_job.status != MLTrainingStatus.COMPLETED:
        raise ValueError(
            f"Model '{model_id}' is not ready for prediction. Current status: {training_job.status}."
        )
    if not training_job.model_object_key:
        raise ValueError(f"Model artifact is missing for model '{model_id}'.")
    if not rows:
        raise ValueError("Prediction rows cannot be empty.")

    model_bundle = load_model_bundle(training_job.model_object_key)
    feature_columns: list[str] = model_bundle["feature_columns"]
    task_type: str = model_bundle["task_type"]
    algorithm: str = model_bundle["algorithm"]
    pipeline = model_bundle["pipeline"]
    label_encoder = model_bundle.get("label_encoder")

    input_dataframe = pd.DataFrame(rows)
    missing_columns = [column for column in feature_columns if column not in input_dataframe]
    if missing_columns:
        raise ValueError(
            "Input rows are missing required feature columns: "
            + ", ".join(missing_columns)
        )

    feature_frame = input_dataframe[feature_columns]
    raw_predictions = pipeline.predict(feature_frame)
    predictions = _coerce_predictions(
        raw_predictions=raw_predictions,
        task_type=task_type,
        label_encoder=label_encoder,
    )

    probabilities: list[dict[str, float]] | None = None
    if task_type == "classification" and hasattr(pipeline, "predict_proba"):
        class_labels = model_bundle.get("class_labels", [])
        probability_matrix = pipeline.predict_proba(feature_frame)
        probabilities = []
        for row_probabilities in probability_matrix:
            probability_item: dict[str, float] = {}
            for index, probability_value in enumerate(row_probabilities):
                label = (
                    str(class_labels[index])
                    if index < len(class_labels)
                    else f"class_{index}"
                )
                probability_item[label] = float(probability_value)
            probabilities.append(probability_item)

    return {
        "model_id": model_id,
        "task_type": task_type,
        "algorithm": algorithm,
        "prediction_count": len(predictions),
        "predictions": predictions,
        "probabilities": probabilities,
    }


def load_model_bundle(model_object_key: str) -> dict[str, Any]:
    """
    Load pickled model bundle from object storage.
    """
    model_bytes = download_bytes(
        bucket=settings.MINIO_BUCKET_MODELS,
        object_key=model_object_key,
    )
    # Model bundle is produced internally by training tasks in this project.
    return pickle.loads(model_bytes)


def _coerce_predictions(raw_predictions, task_type: str, label_encoder):
    """
    Convert numpy outputs to JSON-serializable Python values.
    """
    if task_type == "classification" and label_encoder is not None:
        decoded = label_encoder.inverse_transform(raw_predictions.astype(int))
        return [str(item) for item in decoded]

    predictions: list[Any] = []
    for value in raw_predictions:
        if hasattr(value, "item"):
            predictions.append(value.item())
        else:
            predictions.append(value)
    return predictions
