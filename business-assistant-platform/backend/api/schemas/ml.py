"""
File: backend/api/schemas/ml.py
Purpose: Pydantic contracts for Layer 2 training and prediction APIs.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MLTrainRequest(BaseModel):
    """
    Request payload for starting an asynchronous model-training job.
    """

    ingestion_job_id: str = Field(description="Completed CSV ingestion job identifier.")
    target_column: str = Field(description="Target column name for supervised learning.")
    task_type: str = Field(
        default="auto",
        description="One of: auto, classification, regression.",
    )
    algorithm: str = Field(
        default="auto",
        description=(
            "One of: auto, xgboost, random_forest, logistic_regression, "
            "linear_regression."
        ),
    )

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value not in {"auto", "classification", "regression"}:
            raise ValueError("task_type must be auto, classification, or regression.")
        return normalized_value


class MLTrainResponse(BaseModel):
    """
    Response payload after a training job is accepted.
    """

    training_job_id: str
    status: str
    task_id: str
    ingestion_job_id: str
    target_column: str
    requested_task_type: str
    algorithm: str


class MLTrainingJobResponse(BaseModel):
    """
    Response payload for querying model-training job status and outputs.
    """

    training_job_id: str
    model_id: str | None
    ingestion_job_id: str
    status: str
    target_column: str
    requested_task_type: str
    task_type: str | None
    algorithm: str
    metrics_json: dict[str, float]
    feature_columns: list[str]
    class_labels: list[str]
    row_count: int | None
    model_object_key: str | None
    mlflow_experiment_name: str | None
    mlflow_run_id: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class MLPredictRequest(BaseModel):
    """
    Request payload for batch prediction using a trained model.
    """

    model_id: str
    rows: list[dict[str, Any]]

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise ValueError("rows must include at least one record.")
        return value


class MLPredictResponse(BaseModel):
    """
    Response payload for prediction results.
    """

    model_id: str
    task_type: str
    algorithm: str
    prediction_count: int
    predictions: list[Any]
    probabilities: list[dict[str, float]] | None


class MLEvaluateRequest(BaseModel):
    """
    Request payload for evaluating model predictions against actual labels.
    """

    model_id: str
    ingestion_job_id: str
    target_column: str | None = None
    max_rows: int = 2000

    @field_validator("max_rows")
    @classmethod
    def validate_max_rows(cls, value: int) -> int:
        if value < 1 or value > 10000:
            raise ValueError("max_rows must be between 1 and 10000.")
        return value


class MLEvaluateResponse(BaseModel):
    """
    Response payload for model-vs-actual evaluation.
    """

    model_id: str
    ingestion_job_id: str
    target_column: str
    task_type: str
    algorithm: str
    row_count: int
    metrics_json: dict[str, float]
    actual_counts: dict[str, int] | None
    predicted_counts: dict[str, int] | None
    confusion_labels: list[str] | None
    confusion_matrix: list[list[int]] | None
    preview_rows: list[dict[str, Any]]
    regression_points: list[dict[str, float]] | None
