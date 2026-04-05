# File: infra/docker/backend.Dockerfile
# Purpose: Build image for the placeholder FastAPI backend service used in local compose.

FROM python:3.11-slim

# Keeps Python output unbuffered and avoids generating .pyc files in containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Copy backend source after dependencies so code edits do not invalidate pip layers.
COPY backend /app/backend

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
