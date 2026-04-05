"""
File: backend/core/config.py
Purpose: Centralized environment-backed settings used by all backend modules.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = Field(default="business-assistant-backend")
    APP_ENV: str = Field(default="local")
    APP_DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    BACKEND_HOST: str = Field(default="0.0.0.0")
    BACKEND_PORT: int = Field(default=8000)
    API_PREFIX: str = Field(default="/api/v1")

    POSTGRES_HOST: str = Field(default="postgres")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="business_assistant")
    POSTGRES_USER: str = Field(default="business_user")
    POSTGRES_PASSWORD: str = Field(default="business_password")

    MONGO_HOST: str = Field(default="mongodb")
    MONGO_PORT: int = Field(default=27017)
    MONGO_DATABASE: str = Field(default="business_assistant_docs")
    MONGO_ROOT_USERNAME: str = Field(default="admin")
    MONGO_ROOT_PASSWORD: str = Field(default="admin_password")
    MONGO_INGESTION_COLLECTION: str = Field(default="ingestion_chunks")

    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="redis_password")
    CELERY_BROKER_URL: str = Field(default="redis://:redis_password@redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://:redis_password@redis:6379/1")
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=300)
    CELERY_TASK_TIME_LIMIT: int = Field(default=600)

    QDRANT_HOST: str = Field(default="qdrant")
    QDRANT_PORT: int = Field(default=6333)

    MLFLOW_TRACKING_URI: str = Field(default="http://mlflow:5000")
    MLFLOW_EXPERIMENT_NAME: str = Field(default="business-assistant-layer2")

    MINIO_HOST: str = Field(default="minio")
    MINIO_API_PORT: int = Field(default=9000)
    MINIO_ROOT_USER: str = Field(default="minioadmin")
    MINIO_ROOT_PASSWORD: str = Field(default="minioadmin123")
    AWS_ACCESS_KEY_ID: str = Field(default="minioadmin")
    AWS_SECRET_ACCESS_KEY: str = Field(default="minioadmin123")
    MINIO_USE_SSL: bool = Field(default=False)
    MINIO_BUCKET_RAW: str = Field(default="raw-data")
    MINIO_BUCKET_PROCESSED: str = Field(default="processed-data")
    MINIO_BUCKET_MODELS: str = Field(default="model-artifacts")

    INGESTION_MAX_FILE_SIZE_MB: int = Field(default=25)
    INGESTION_ALLOWED_EXTENSIONS: str = Field(default="csv,pdf,docx")
    INGESTION_CHUNK_SIZE: int = Field(default=1000)
    INGESTION_CHUNK_OVERLAP: int = Field(default=150)
    INGESTION_MAX_CHUNKS: int = Field(default=300)

    @property
    def postgres_dsn(self) -> str:
        """
        SQLAlchemy DSN for PostgreSQL connections.
        """
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def mongodb_uri(self) -> str:
        """
        MongoDB URI with root credentials.
        """
        return (
            f"mongodb://{self.MONGO_ROOT_USERNAME}:{self.MONGO_ROOT_PASSWORD}"
            f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DATABASE}"
            "?authSource=admin"
        )

    @property
    def redis_url(self) -> str:
        """
        Redis URL used by cache and Celery integration.
        """
        return (
            f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        )

    @property
    def minio_endpoint(self) -> str:
        """
        MinIO endpoint formatted for SDK client initialization.
        """
        return f"{self.MINIO_HOST}:{self.MINIO_API_PORT}"

    @property
    def minio_access_key(self) -> str:
        """
        Access key for object storage operations.
        """
        return self.AWS_ACCESS_KEY_ID or self.MINIO_ROOT_USER

    @property
    def minio_secret_key(self) -> str:
        """
        Secret key for object storage operations.
        """
        return self.AWS_SECRET_ACCESS_KEY or self.MINIO_ROOT_PASSWORD

    @property
    def ingestion_max_file_size_bytes(self) -> int:
        """
        Convert file-size limit from MB to bytes for upload validation.
        """
        return self.INGESTION_MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions(self) -> set[str]:
        """
        Normalize the comma-delimited extension list to a lowercase set.
        """
        return {
            item.strip().lower()
            for item in self.INGESTION_ALLOWED_EXTENSIONS.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    """
    Return a singleton settings object so env parsing occurs once per process.
    """
    return Settings()
