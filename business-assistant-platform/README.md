<!--
File: README.md
Purpose: Root project documentation for the AI-Powered Autonomous Business Assistant Platform.
-->

# AI-Powered Autonomous Business Assistant Platform

This monorepo contains a full-stack, Azure-ready platform that helps businesses:

1. Upload operational data (`CSV`, `PDF`, `DOCX`).
2. Run ML predictions on business-specific data.
3. Query a domain-aware AI assistant using RAG over their own documents.

## Why This Architecture

We are building in 5 layers so each concern is isolated, testable, and replaceable:

1. **Layer 1 - Data Ingestion & Processing**: Accepts files, parses content, cleans data, and stores structured/unstructured outputs.
2. **Layer 2 - ML/DL Prediction Engine**: Trains and serves models with experiment tracking.
3. **Layer 3 - GenAI & Agentic Layer**: RAG pipeline + tool-using agents over business data.
4. **Layer 4 - React Frontend**: User interface for upload, analytics, and chat.
5. **Layer 5 - Azure Deployment**: Production infrastructure, CI/CD, and managed cloud services.

This layering keeps dependencies directional:

- Lower layers expose capabilities upward.
- Upper layers do not leak UI/deployment concerns downward.

## Repository Layout

```text
business-assistant-platform/
  backend/
    ingestion/        # Layer 1 modules (parsing, cleaning, validation)
    ml/               # Layer 2 modules (training, inference, tracking)
    agents/           # Layer 3 modules (RAG, prompts, agent tools)
    api/              # Shared FastAPI app, routers, request/response contracts
    core/             # Configuration, shared clients, common utilities
  frontend/           # Layer 4 React + Tailwind + charts
  infra/
    docker/           # Dockerfiles for local/service images
    azure/            # Azure deployment templates and notes
    github-actions/   # CI/CD workflow files and templates
  docker-compose.yml  # Local stack orchestration
  .env.example        # Environment variable template (all layers)
  README.md           # This file
```

## Local Stack (Docker Compose)

The scaffold Compose environment starts these services:

1. `postgres`: structured business data and model metadata.
2. `mongodb`: unstructured and document-oriented data.
3. `redis`: cache + Celery broker/result backend.
4. `qdrant`: vector search store for RAG embeddings.
5. `minio`: local S3-compatible store (drop-in for Azure Blob patterns).
6. `mlflow`: experiment tracking server.
7. `backend`: FastAPI service for Layer 1 and Layer 2 APIs.
8. `celery_worker`: asynchronous worker for ingestion and model-training jobs.

## Quick Start

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Launch all local services:

   ```bash
   docker compose up --build
   ```

3. Verify endpoints:

   - Backend health: `http://localhost:8000/health`
   - MLflow UI: `http://localhost:5000`
   - MinIO API: `http://localhost:9000`
   - MinIO Console: `http://localhost:9001`
   - Qdrant API: `http://localhost:6333`
   - FastAPI docs: `http://localhost:8000/docs`

## Layer 1 (Implemented)

Layer 1 now supports asynchronous ingestion for `csv`, `pdf`, and `docx`.

### Endpoints

1. `POST /api/v1/ingestion/upload`: upload a file for processing.
2. `GET /api/v1/ingestion/jobs/{job_id}`: inspect async ingestion job status.
3. `GET /api/v1/ingestion/documents/{document_id}`: inspect processed document metadata.

### Example Local Test

1. Upload file:

   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
     -F "file=@./sample.csv"
   ```

2. Read job:

   ```bash
   curl "http://localhost:8000/api/v1/ingestion/jobs/<job_id>"
   ```

### Layer 1 Data Persistence

1. MinIO stores raw and processed artifacts.
2. PostgreSQL stores ingestion jobs and processed document metadata.
3. MongoDB stores normalized text chunks for future RAG indexing.

## Layer 2 (Implemented)

Layer 2 now supports asynchronous model training and batch prediction from completed CSV ingestion jobs.

### Endpoints

1. `POST /api/v1/ml/train`: create async model-training job.
2. `GET /api/v1/ml/jobs/{training_job_id}`: inspect training status and metrics.
3. `POST /api/v1/ml/predict`: run prediction using trained `model_id`.
4. `POST /api/v1/ml/evaluate`: compare predicted vs actual on a CSV ingestion job.
5. `GET /layer2/dashboard`: open the visual validation webpage.

### Example Local Test

1. Start training job:

   ```bash
   curl -X POST "http://localhost:8000/api/v1/ml/train" \
     -H "Content-Type: application/json" \
     -d '{
       "ingestion_job_id": "<completed_ingestion_job_id>",
       "target_column": "churned",
       "task_type": "auto",
       "algorithm": "xgboost"
     }'
   ```

2. Check status:

   ```bash
   curl "http://localhost:8000/api/v1/ml/jobs/<training_job_id>"
   ```

3. Predict:

   ```bash
   curl -X POST "http://localhost:8000/api/v1/ml/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "model_id": "<model_id>",
       "rows": [
         {"customer_id": 2001, "monthly_revenue": 11000, "last_contact_days": 8}
       ]
     }'
   ```

4. Visual validation dashboard:

   Visit `http://localhost:8000/layer2/dashboard` in your browser.

### Layer 2 Data Persistence

1. PostgreSQL stores training-job state and model metadata (`ml_training_jobs`).
2. MinIO stores serialized trained model bundles.
3. MLflow stores training parameters and metrics for experiment tracking.

## Technology Choices (Local First, Azure Ready)

- **FastAPI**: typed Python APIs, async support, and clear OpenAPI docs.
- **PostgreSQL + MongoDB**: split structured and unstructured workloads cleanly.
- **Redis + Celery**: reliable async processing for ingestion and long-running jobs.
- **Qdrant**: open-source vector DB for low-friction local RAG experimentation.
- **Ollama**: local LLM runtime during development.
- **Azure OpenAI (GPT-4o in Azure AI Foundry)**: production LLM target.
- **MinIO**: local object storage with an Azure-compatible integration pattern.
- **MLflow**: experiment tracking and model lifecycle metadata.

## Development Notes

- Credentials are environment-variable driven only; no hardcoded secrets.
- Layers are implemented incrementally and verified before moving forward.
- Next step: implement **Layer 3 GenAI & Agentic Layer** on top of ingested and modeled data.
