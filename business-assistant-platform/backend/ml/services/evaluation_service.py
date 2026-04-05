"""
File: backend/ml/services/evaluation_service.py
Purpose: Evaluation utilities for comparing model predictions against actual labels.
"""

import io
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.models import IngestionJob, MLTrainingStatus
from backend.core.storage import download_bytes
from backend.ml.services.prediction_service import load_model_bundle
from backend.ml.services.training_service import fetch_training_job_by_model_id

settings = get_settings()


def evaluate_model_on_ingestion_job(
    db_session: Session,
    model_id: str,
    ingestion_job_id: str,
    target_column: str | None = None,
    max_rows: int = 2000,
) -> dict[str, Any]:
    """
    Evaluate a trained model against actual labels from a CSV ingestion dataset.
    """
    training_job = fetch_training_job_by_model_id(db_session=db_session, model_id=model_id)
    if not training_job:
        raise ValueError(f"Model '{model_id}' was not found.")
    if training_job.status != MLTrainingStatus.COMPLETED:
        raise ValueError(
            f"Model '{model_id}' is not ready for evaluation. Current status: {training_job.status}."
        )
    if not training_job.model_object_key:
        raise ValueError(f"Model artifact is missing for model '{model_id}'.")

    ingestion_job = db_session.get(IngestionJob, ingestion_job_id)
    if not ingestion_job:
        raise ValueError(f"Ingestion job '{ingestion_job_id}' was not found.")
    if ingestion_job.status != "completed":
        raise ValueError(
            f"Ingestion job '{ingestion_job_id}' must be completed before evaluation."
        )
    if ingestion_job.file_extension != "csv":
        raise ValueError("Evaluation currently supports CSV ingestion jobs only.")

    model_bundle = load_model_bundle(training_job.model_object_key)
    dataset = _load_dataset_from_ingestion_job(ingestion_job)

    resolved_target_column = (target_column or training_job.target_column).strip()
    if resolved_target_column not in dataset.columns:
        raise ValueError(
            f"Target column '{resolved_target_column}' was not found in the ingestion dataset."
        )

    feature_columns: list[str] = model_bundle["feature_columns"]
    missing_feature_columns = [
        column_name for column_name in feature_columns if column_name not in dataset.columns
    ]
    if missing_feature_columns:
        raise ValueError(
            "Dataset is missing required feature columns: "
            + ", ".join(missing_feature_columns)
        )

    task_type: str = model_bundle["task_type"]
    algorithm: str = model_bundle["algorithm"]
    pipeline = model_bundle["pipeline"]
    label_encoder = model_bundle.get("label_encoder")
    class_labels = model_bundle.get("class_labels", [])

    if task_type == "classification":
        return _evaluate_classification(
            dataset=dataset,
            feature_columns=feature_columns,
            target_column=resolved_target_column,
            pipeline=pipeline,
            label_encoder=label_encoder,
            class_labels=class_labels,
            model_id=model_id,
            ingestion_job_id=ingestion_job_id,
            algorithm=algorithm,
            max_rows=max_rows,
        )

    return _evaluate_regression(
        dataset=dataset,
        feature_columns=feature_columns,
        target_column=resolved_target_column,
        pipeline=pipeline,
        model_id=model_id,
        ingestion_job_id=ingestion_job_id,
        algorithm=algorithm,
        max_rows=max_rows,
    )


def _load_dataset_from_ingestion_job(ingestion_job: IngestionJob) -> pd.DataFrame:
    """
    Load CSV dataset bytes from object storage into a dataframe.
    """
    if not ingestion_job.raw_object_key:
        raise ValueError(f"Ingestion job '{ingestion_job.id}' has no raw object key.")
    csv_bytes = download_bytes(
        bucket=settings.MINIO_BUCKET_RAW,
        object_key=ingestion_job.raw_object_key,
    )
    return pd.read_csv(io.BytesIO(csv_bytes))


def _evaluate_classification(
    dataset: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    pipeline,
    label_encoder,
    class_labels: list[str],
    model_id: str,
    ingestion_job_id: str,
    algorithm: str,
    max_rows: int,
) -> dict[str, Any]:
    """
    Evaluate classification model and return metrics + confusion information.
    """
    actual_series = dataset[target_column].astype("string").str.strip()
    valid_mask = actual_series.notna() & (actual_series != "")
    filtered_dataset = dataset.loc[valid_mask].copy()
    if filtered_dataset.empty:
        raise ValueError("No valid actual labels found for classification evaluation.")

    feature_frame = filtered_dataset[feature_columns]
    predicted_raw = pipeline.predict(feature_frame)
    if label_encoder is not None:
        predicted_labels = label_encoder.inverse_transform(predicted_raw.astype(int))
    else:
        predicted_labels = predicted_raw

    actual_labels = filtered_dataset[target_column].astype(str).tolist()
    predicted_labels_str = [str(item) for item in predicted_labels]
    effective_labels = sorted(set(actual_labels).union(predicted_labels_str))
    if class_labels:
        effective_labels = sorted(set(effective_labels).union({str(item) for item in class_labels}))

    matrix = confusion_matrix(
        y_true=actual_labels,
        y_pred=predicted_labels_str,
        labels=effective_labels,
    )

    metrics = {
        "accuracy": float(accuracy_score(actual_labels, predicted_labels_str)),
        "precision_weighted": float(
            precision_score(
                actual_labels,
                predicted_labels_str,
                average="weighted",
                zero_division=0,
            )
        ),
        "recall_weighted": float(
            recall_score(
                actual_labels,
                predicted_labels_str,
                average="weighted",
                zero_division=0,
            )
        ),
        "f1_weighted": float(
            f1_score(
                actual_labels,
                predicted_labels_str,
                average="weighted",
                zero_division=0,
            )
        ),
    }

    actual_counts = {
        label: int((np.array(actual_labels) == label).sum()) for label in effective_labels
    }
    predicted_counts = {
        label: int((np.array(predicted_labels_str) == label).sum())
        for label in effective_labels
    }

    preview_rows = []
    for row_index, (_, row) in enumerate(filtered_dataset.iterrows()):
        if row_index >= max_rows:
            break
        preview_rows.append(
            {
                "row_index": row_index,
                "actual": str(row[target_column]),
                "predicted": predicted_labels_str[row_index],
            }
        )

    return {
        "model_id": model_id,
        "ingestion_job_id": ingestion_job_id,
        "target_column": target_column,
        "task_type": "classification",
        "algorithm": algorithm,
        "row_count": int(len(filtered_dataset)),
        "metrics_json": metrics,
        "actual_counts": actual_counts,
        "predicted_counts": predicted_counts,
        "confusion_labels": effective_labels,
        "confusion_matrix": matrix.tolist(),
        "preview_rows": preview_rows,
        "regression_points": None,
    }


def _evaluate_regression(
    dataset: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    pipeline,
    model_id: str,
    ingestion_job_id: str,
    algorithm: str,
    max_rows: int,
) -> dict[str, Any]:
    """
    Evaluate regression model and return metrics + scatter points.
    """
    actual_numeric = pd.to_numeric(dataset[target_column], errors="coerce")
    valid_mask = actual_numeric.notna()
    filtered_dataset = dataset.loc[valid_mask].copy()
    if filtered_dataset.empty:
        raise ValueError("No numeric actual labels found for regression evaluation.")

    actual_values = actual_numeric.loc[valid_mask].astype(float).to_numpy()
    predicted_values = pipeline.predict(filtered_dataset[feature_columns]).astype(float)

    rmse = float(np.sqrt(mean_squared_error(actual_values, predicted_values)))
    mae = float(mean_absolute_error(actual_values, predicted_values))
    r2 = float(r2_score(actual_values, predicted_values))

    points = []
    for index in range(min(len(actual_values), max_rows)):
        points.append(
            {
                "row_index": int(index),
                "actual": float(actual_values[index]),
                "predicted": float(predicted_values[index]),
            }
        )

    return {
        "model_id": model_id,
        "ingestion_job_id": ingestion_job_id,
        "target_column": target_column,
        "task_type": "regression",
        "algorithm": algorithm,
        "row_count": int(len(filtered_dataset)),
        "metrics_json": {"rmse": rmse, "mae": mae, "r2": r2},
        "actual_counts": None,
        "predicted_counts": None,
        "confusion_labels": None,
        "confusion_matrix": None,
        "preview_rows": points,
        "regression_points": points,
    }
