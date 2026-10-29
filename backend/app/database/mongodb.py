"""MongoDB connection management and low-level database helpers."""

from __future__ import annotations

import logging
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)

from app.config.settings import get_settings
from app.models.collections import INDEXES

logger = logging.getLogger(__name__)

# Module-level singletons avoid creating multiple MongoDB clients.
_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def init_mongodb() -> None:
    """Create the MongoDB client and database, verifying connectivity.

    This function is idempotent and safe to call at startup.  If MongoDB is
    unavailable the application still starts, but the health endpoint will
    report ``database: disconnected``.
    """
    global _client, _database

    # Reuse the existing client when already initialised.
    if _client is not None:
        return

    settings = get_settings()

    try:
        _client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            connectTimeoutMS=settings.mongodb_connect_timeout_ms,
            uuidRepresentation="standard",
        )
        _database = _client[settings.mongodb_database]

        # Force a connection so failures surface here instead of on first query.
        _client.admin.command("ping")
        logger.info("Connected to MongoDB database '%s'", settings.mongodb_database)
    except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as exc:
        logger.error("Unable to connect to MongoDB: %s", exc)
        # Keep the client so the connection can be retried later; do not crash.
    except PyMongoError as exc:
        logger.error("MongoDB initialisation failed: %s", exc)


def close_mongodb() -> None:
    """Close the MongoDB client and release resources."""
    global _client, _database

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def get_database() -> Database:
    """Return the configured database, raising if not initialised."""
    if _database is None:
        raise RuntimeError("MongoDB is not initialised. Call init_mongodb() first.")
    return _database


def get_collection(name: str) -> Collection:
    """Return a collection by name."""
    return get_database()[name]


def check_database_connection() -> bool:
    """Return True when MongoDB is reachable, False otherwise."""
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def create_indexes() -> dict[str, list[str]]:
    """Create all configured indexes (idempotent).

    Returns a mapping of collection name -> list of created index names.
    """
    created: dict[str, list[str]] = {}
    for collection_name, index_models in INDEXES.items():
        collection = get_collection(collection_name)
        created[collection_name] = collection.create_indexes(index_models)
        logger.info(
            "Ensured %d index(es) on collection '%s'",
            len(index_models),
            collection_name,
        )
    return created
