<!--
File: backend/core/README.md
Purpose: Documentation for shared backend infrastructure used by Layer 1 and above.
-->

# Core Module

The `core` package contains shared infrastructure primitives consumed by API routes, ingestion services, and async workers.

## Layer 1 Files

1. `config.py`: typed environment configuration used across the backend.
2. `db.py`: SQLAlchemy engine, session management, and DB initialization helper.
3. `models.py`: ORM models for ingestion jobs, processed documents, and ML training jobs.
4. `mongo.py`: Mongo client and collection helpers for chunk persistence.
5. `storage.py`: MinIO utility functions for raw, processed, and model artifacts.
6. `celery_app.py`: Celery broker/backend configuration and task discovery.
7. `__init__.py`: package marker.

## Why This Matters

1. Keeps service code focused on business logic rather than infrastructure boilerplate.
2. Enables reuse across current Layer 1 and upcoming Layer 2/3 implementations.
