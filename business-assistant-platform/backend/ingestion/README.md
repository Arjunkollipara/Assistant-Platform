<!--
File: backend/ingestion/README.md
Purpose: Layer 1 implementation guide for file ingestion, parsing, cleaning, and async processing.
-->

# Layer 1: Data Ingestion & Processing

Layer 1 receives user files, validates them, stores raw artifacts, parses and cleans content asynchronously, and persists normalized outputs for downstream ML and RAG workflows.

## Architecture Flow

1. API route accepts upload (`POST /api/v1/ingestion/upload`).
2. Service layer validates file type and size, uploads raw file to MinIO, creates a Postgres job record, and dispatches Celery task.
3. Celery worker downloads raw file, parses format-specific content, normalizes/chunks text, writes processed artifact back to MinIO, and stores metadata in Postgres plus chunks in MongoDB.
4. API status endpoints expose job/document state.

## File Map

1. `__init__.py`: package marker for ingestion module.
2. `services/ingestion_service.py`: upload validation, raw persistence, and task dispatch orchestration.
3. `tasks/ingestion_tasks.py`: async ingestion pipeline execution in Celery worker.
4. `tasks/__init__.py`: Celery task package marker.
5. `parsers/base.py`: parser output contract (`ParsedDocument`).
6. `parsers/factory.py`: extension-to-parser routing.
7. `parsers/csv_parser.py`: CSV parsing and tabular profiling.
8. `parsers/pdf_parser.py`: PDF page text extraction.
9. `parsers/docx_parser.py`: DOCX paragraph text extraction.
10. `parsers/__init__.py`: parser module exports.
11. `processors/cleaner.py`: text normalization and chunking helpers.
12. `processors/__init__.py`: processor module exports.

## Storage Strategy

1. Raw uploads: MinIO bucket `MINIO_BUCKET_RAW`.
2. Processed JSON artifacts: MinIO bucket `MINIO_BUCKET_PROCESSED`.
3. Job and document metadata: PostgreSQL tables (`ingestion_jobs`, `ingestion_documents`).
4. Text chunks for unstructured retrieval: Mongo collection `MONGO_INGESTION_COLLECTION`.

## How It Connects to Other Layers

1. Layer 2 (ML) can consume cleaned tabular summaries and metadata from Postgres/MinIO.
2. Layer 3 (RAG/agents) can consume chunks from Mongo and processed artifacts from MinIO before vectorization.
