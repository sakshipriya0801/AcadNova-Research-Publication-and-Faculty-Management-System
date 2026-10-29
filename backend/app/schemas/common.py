"""Shared Pydantic base classes for schemas."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict


def utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class MongoDocument(BaseModel):
    """Base model for MongoDB document representations.

    ``extra="allow"`` tolerates fields added by MongoDB or future schema
    evolution (e.g. ``_id``) without failing validation.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")
