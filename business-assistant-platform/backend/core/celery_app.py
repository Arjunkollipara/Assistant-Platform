"""
File: backend/core/celery_app.py
Purpose: Celery application configuration for asynchronous ingestion tasks.
"""

from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "business_assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.ingestion.tasks.ingestion_tasks",
        "backend.ml.tasks.training_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    timezone="UTC",
    enable_utc=True,
)
