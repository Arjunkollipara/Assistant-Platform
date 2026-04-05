"""
File: backend/core/mongo.py
Purpose: MongoDB client access helpers for document chunk persistence.
"""

from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from backend.core.config import get_settings

settings = get_settings()


@lru_cache
def get_mongo_client() -> MongoClient:
    """
    Return a singleton MongoDB client for process-wide reuse.
    """
    return MongoClient(settings.mongodb_uri)


def get_mongo_database() -> Database:
    """
    Return the primary Mongo database for this application.
    """
    return get_mongo_client()[settings.MONGO_DATABASE]


def get_ingestion_chunk_collection() -> Collection:
    """
    Return the collection that stores normalized ingestion chunks.
    """
    return get_mongo_database()[settings.MONGO_INGESTION_COLLECTION]

