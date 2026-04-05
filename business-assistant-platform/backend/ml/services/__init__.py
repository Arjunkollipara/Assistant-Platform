"""
File: backend/ml/services/__init__.py
Purpose: Service exports for Layer 2 training and prediction workflows.
"""

from backend.ml.services.evaluation_service import evaluate_model_on_ingestion_job
from backend.ml.services.prediction_service import predict_with_model
from backend.ml.services.training_service import create_training_job, fetch_training_job

__all__ = [
    "create_training_job",
    "fetch_training_job",
    "predict_with_model",
    "evaluate_model_on_ingestion_job",
]
