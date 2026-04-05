<!--
File: backend/api/README.md
Purpose: Documentation for FastAPI application composition and Layer 1 routing surface.
-->

# API Module

The API module exposes backend capabilities through versioned HTTP endpoints.

## Layer 1 Files

1. `main.py`: FastAPI app bootstrap, startup lifecycle initialization, and router registration.
2. `routers/ingestion.py`: upload, job-status, and document-status routes for ingestion.
3. `routers/__init__.py`: router exports for centralized app composition.
4. `schemas/ingestion.py`: response contracts for ingestion endpoints.
5. `schemas/__init__.py`: schema package marker.
6. `__init__.py`: API package marker.

## Layer 1 Endpoints

1. `POST /api/v1/ingestion/upload`: accepts `csv`, `pdf`, and `docx` files.
2. `GET /api/v1/ingestion/jobs/{job_id}`: returns async job status.
3. `GET /api/v1/ingestion/documents/{document_id}`: returns processed document metadata.
