<!--
File: backend/README.md
Purpose: Backend module map for ingestion, ML, agents, API, and shared core services.
-->

# Backend Overview

The backend is organized by responsibility so each platform layer can be developed and tested independently.

## Folder Responsibilities

1. `ingestion/`: Layer 1 file intake, parsing, validation, chunking, and async processing.
2. `ml/`: Layer 2 model training, evaluation, prediction, and experiment logging.
3. `agents/`: Layer 3 RAG orchestration, prompt assembly, and tool-enabled agent flows.
4. `api/`: FastAPI app entry point, schemas, and routers.
5. `core/`: configuration, data clients, and shared infrastructure primitives.

## Current Layer 1 Implementation

1. Upload API with async queue dispatch.
2. Celery worker for parser/cleaner pipeline execution.
3. Postgres persistence for job/document metadata.
4. Mongo persistence for unstructured chunks.
5. MinIO storage for raw and processed artifacts.

## Quick File Map

1. `api/main.py`: API bootstrap and route mounting.
2. `api/routers/ingestion.py`: ingestion endpoints.
3. `core/models.py`: ingestion ORM entities.
4. `ingestion/services/ingestion_service.py`: job creation and dispatch logic.
5. `ingestion/tasks/ingestion_tasks.py`: background processing logic.
