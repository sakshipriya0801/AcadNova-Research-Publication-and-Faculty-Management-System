"""User database operations (``users`` collection)."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.database import mongodb
from app.models.collections import USERS


def _collection():
    return mongodb.get_collection(USERS)


def find_user_by_email(email: str) -> Optional[dict]:
    """Return the user document for the given email, or None."""
    return _collection().find_one({"email": email})


def find_user_by_id(user_id: str) -> Optional[dict]:
    """Return the user document for the given id, or None."""
    return _collection().find_one({"user_id": user_id})


def find_user_by_faculty_id(faculty_id: str) -> Optional[dict]:
    """Return the user document linked to a faculty record, or None."""
    return _collection().find_one({"faculty_id": faculty_id})


def update_user_by_faculty_id(faculty_id: str, fields: dict) -> bool:
    """Update the user linked to a faculty record."""
    update = dict(fields)
    update["updated_at"] = datetime.now(timezone.utc)
    result = _collection().update_one({"faculty_id": faculty_id}, {"$set": update})
    return result.matched_count > 0


def create_user(user_data: dict) -> dict:
    """Insert a new user document and return it."""
    now = datetime.now(timezone.utc)
    user_data.setdefault("user_id", str(uuid4()))
    user_data.setdefault("created_at", now)
    user_data.setdefault("updated_at", now)
    _collection().insert_one(user_data)
    return user_data


def update_user(user_id: str, fields: dict) -> bool:
    """Update a user document; returns True if a document was matched."""
    update = dict(fields)
    update["updated_at"] = datetime.now(timezone.utc)
    result = _collection().update_one({"user_id": user_id}, {"$set": update})
    return result.matched_count > 0


def deactivate_user(user_id: str) -> bool:
    """Mark a user as inactive."""
    return update_user(user_id, {"is_active": False})


def approval_status(user: Optional[dict]) -> str:
    """Return a user's approval status (legacy records default to approved)."""
    if user is None:
        return "approved"
    return user.get("approval_status") or "approved"


def must_change_password(user: Optional[dict]) -> bool:
    """Return whether the user must change their password (default False)."""
    if user is None:
        return False
    return bool(user.get("must_change_password"))


def reconcile_approval_statuses() -> int:
    """Backfill users missing ``approval_status``/``must_change_password``.

    Idempotent; keeps existing faculty and administrators usable after these
    flags were introduced.  Missing ``approval_status`` defaults to ``approved``
    and missing ``must_change_password`` defaults to ``False``.
    """
    modified = _collection().update_many(
        {"approval_status": {"$exists": False}},
        {"$set": {"approval_status": "approved"}},
    ).modified_count
    modified += _collection().update_many(
        {"must_change_password": {"$exists": False}},
        {"$set": {"must_change_password": False}},
    ).modified_count
    return modified
