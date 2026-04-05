"""
File: backend/core/db.py
Purpose: Relational database engine, session lifecycle, and initialization helpers.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.core.config import get_settings

settings = get_settings()

# Shared SQLAlchemy objects used across API handlers and Celery tasks.
engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
Base = declarative_base()


def get_db_session() -> Generator[Session, None, None]:
    """
    Yield a transactional DB session and guarantee closure after request scope.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_relational_database() -> None:
    """
    Create relational tables if they do not exist.
    """
    # Import models at runtime to avoid circular dependencies during module import.
    from backend.core import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

