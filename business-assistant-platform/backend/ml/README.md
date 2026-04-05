<!--
File: backend/ml/README.md
Purpose: Layer 2 implementation guide for asynchronous training, experiment tracking, and inference.
-->

# Layer 2: ML/DL Prediction Engine

Layer 2 trains supervised tabular models from Layer 1 CSV ingestion outputs and serves batch predictions through API endpoints.

## Architecture Flow

1. API route creates async training job (`POST /api/v1/ml/train`).
2. Celery worker loads CSV dataset from MinIO raw bucket, trains model, computes metrics, and logs experiment in MLflow.
3. Worker serializes the model bundle to MinIO model bucket and updates Postgres training-job metadata.
4. Prediction API (`POST /api/v1/ml/predict`) loads model bundle by `model_id` and returns predictions.
5. Evaluation API (`POST /api/v1/ml/evaluate`) compares predictions against actual labels for validation.

## File Map

1. `services/training_service.py`: validation and async training-job dispatch.
2. `services/training_pipeline.py`: preprocessing, estimator selection, training, and evaluation logic.
3. `services/prediction_service.py`: model-bundle loading and batch inference.
4. `services/evaluation_service.py`: model-vs-actual evaluation metrics and comparison datasets.
5. `services/__init__.py`: ML service exports.
6. `tasks/training_tasks.py`: Celery training pipeline execution and persistence.
7. `tasks/__init__.py`: task package marker.
8. `__init__.py`: module package marker.

## Supported Training Modes

1. Task types: `auto`, `classification`, `regression`.
2. Algorithms: `auto`, `xgboost`, `random_forest`, `logistic_regression`, `linear_regression`.
3. Dataset source: completed CSV ingestion job from Layer 1.

## Stored Outputs

1. Training metadata and status: Postgres table `ml_training_jobs`.
2. Model binaries: MinIO bucket `MINIO_BUCKET_MODELS`.
3. Experiment tracking: MLflow experiment `MLFLOW_EXPERIMENT_NAME`.
