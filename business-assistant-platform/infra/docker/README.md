<!--
File: infra/docker/README.md
Purpose: Documentation for Dockerfiles that define project service images.
-->

# Dockerfiles

This folder contains local image definitions for services that need custom build logic.

## Files

1. `backend.Dockerfile`: builds the FastAPI backend image used by local Docker Compose.

## Notes

- Data stores (PostgreSQL, MongoDB, Redis, Qdrant, MinIO) use official images directly.
- Additional service Dockerfiles can be added here as custom runtime requirements emerge.
