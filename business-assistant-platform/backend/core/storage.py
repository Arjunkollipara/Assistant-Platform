"""
File: backend/core/storage.py
Purpose: Object storage abstraction over MinIO for ingestion raw/processed artifacts.
"""

import io
import json
import re
from functools import lru_cache
from uuid import uuid4

from minio import Minio

from backend.core.config import get_settings

settings = get_settings()


@lru_cache
def get_object_storage_client() -> Minio:
    """
    Return a singleton MinIO client.
    """
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.MINIO_USE_SSL,
    )


def ensure_ingestion_buckets() -> None:
    """
    Create required ingestion buckets if they do not exist yet.
    """
    client = get_object_storage_client()
    for bucket_name in (
        settings.MINIO_BUCKET_RAW,
        settings.MINIO_BUCKET_PROCESSED,
        settings.MINIO_BUCKET_MODELS,
    ):
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)


def sanitize_filename(filename: str) -> str:
    """
    Keep object keys predictable by removing unsafe characters.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    return sanitized.strip("._") or "upload.bin"


def build_raw_object_key(job_id: str, filename: str) -> str:
    """
    Build a deterministic key for uploaded raw files.
    """
    return f"raw/{job_id}/{sanitize_filename(filename)}"


def build_processed_object_key(job_id: str, filename: str) -> str:
    """
    Build a deterministic key for processed JSON artifacts.
    """
    base_name = sanitize_filename(filename)
    return f"processed/{job_id}/{uuid4()}_{base_name}.json"


def build_model_object_key(training_job_id: str, algorithm: str) -> str:
    """
    Build a deterministic key for serialized trained model bundles.
    """
    normalized_algorithm = sanitize_filename(algorithm.lower())
    return f"models/{training_job_id}/{uuid4()}_{normalized_algorithm}.pkl"


def upload_bytes(bucket: str, object_key: str, payload: bytes, content_type: str) -> None:
    """
    Upload bytes payload to object storage.
    """
    stream = io.BytesIO(payload)
    get_object_storage_client().put_object(
        bucket_name=bucket,
        object_name=object_key,
        data=stream,
        length=len(payload),
        content_type=content_type,
    )


def upload_json(bucket: str, object_key: str, payload: dict) -> None:
    """
    Upload JSON payload to object storage.
    """
    encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    upload_bytes(
        bucket=bucket,
        object_key=object_key,
        payload=encoded,
        content_type="application/json",
    )


def download_bytes(bucket: str, object_key: str) -> bytes:
    """
    Download bytes payload from object storage.
    """
    response = get_object_storage_client().get_object(bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
