<!--
File: backend/api/README.md
Purpose: Documentation for FastAPI application composition and Layer 1 routing surface.
-->

# API Module

The API module exposes backend capabilities through versioned HTTP endpoints.

## Layer 1 Files

1. `main.py`: FastAPI app bootstrap, startup lifecycle initialization, and router registration.
2. `routers/ingestion.py`: upload, job-status, and document-status routes for ingestion.
3. `routers/ml.py`: model-training and prediction routes for Layer 2.
4. `routers/__init__.py`: router exports for centralized app composition.
5. `schemas/ingestion.py`: response contracts for ingestion endpoints.
6. `schemas/ml.py`: request/response contracts for Layer 2 ML endpoints.
7. `schemas/__init__.py`: schema package marker.
8. `__init__.py`: API package marker.
9. `static/layer2_validation_dashboard.html`: browser dashboard for model-vs-actual graph validation.

## Layer 1 Endpoints

1. `POST /api/v1/ingestion/upload`: accepts `csv`, `pdf`, and `docx` files.
2. `GET /api/v1/ingestion/jobs/{job_id}`: returns async job status.
3. `GET /api/v1/ingestion/documents/{document_id}`: returns processed document metadata.
4. `POST /api/v1/ml/train`: creates asynchronous model-training job.
5. `GET /api/v1/ml/jobs/{training_job_id}`: returns model-training status.
6. `POST /api/v1/ml/predict`: runs batch prediction using trained `model_id`.
7. `POST /api/v1/ml/evaluate`: compares predicted vs actual values on CSV ingestion data.
8. `GET /layer2/dashboard`: opens the Layer 2 validation dashboard webpage.
