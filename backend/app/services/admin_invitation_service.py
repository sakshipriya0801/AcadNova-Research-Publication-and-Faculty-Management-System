"""Administrator invitation workflow.

Tokens are generated with ``secrets.token_urlsafe`` and only their SHA-256 hash
is stored, so a database leak does not expose usable invitations.  Consumption
uses an atomic conditional ``find_one_and_update`` so an invitation can never be
used twice, even under concurrent requests (this works on standalone MongoDB,
where multi-document transactions are unavailable).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.database import mongodb
from app.models.collections import ADMIN_INVITATIONS

DEFAULT_EXPIRY_HOURS = 72
MAX_EXPIRY_HOURS = 168  # 7 days


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _collection():
    return mongodb.get_collection(ADMIN_INVITATIONS)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """MongoDB returns naive UTC datetimes by default; make them aware."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _status(document: dict, now: datetime) -> str:
    if document.get("used"):
        return "used"
    if document.get("revoked"):
        return "revoked"
    expires_at = _as_utc(document.get("expires_at"))
    if expires_at is not None and expires_at <= now:
        return "expired"
    return "pending"


def create_invitation(
    email: str,
    created_by_user_id: Optional[str],
    expires_in_hours: Optional[int] = None,
) -> tuple[dict, str]:
    """Create an invitation and return ``(document, raw_token)``.

    The raw token is returned only here; only its hash is persisted.
    """
    hours = int(expires_in_hours or DEFAULT_EXPIRY_HOURS)
    hours = max(1, min(hours, MAX_EXPIRY_HOURS))

    token = secrets.token_urlsafe(32)
    now = _now()
    document = {
        "invitation_id": str(uuid4()),
        "email": email.lower(),
        "token_hash": _hash_token(token),
        "created_by_user_id": created_by_user_id,
        "expires_at": now + timedelta(hours=hours),
        "used": False,
        "used_at": None,
        "revoked": False,
        "revoked_at": None,
        "created_at": now,
    }
    _collection().insert_one(document)
    return document, token


def list_invitations() -> list[dict]:
    """Return invitations (newest first) without the token hash."""
    return list(
        _collection()
        .find({}, {"_id": 0, "token_hash": 0})
        .sort("created_at", -1)
    )


def to_response(document: dict) -> dict:
    return {
        "invitation_id": document.get("invitation_id"),
        "email": document.get("email"),
        "status": _status(document, _now()),
        "expires_at": document.get("expires_at"),
        "created_at": document.get("created_at"),
        "used_at": document.get("used_at"),
        "revoked_at": document.get("revoked_at"),
    }


def revoke_invitation(invitation_id: str) -> dict:
    """Revoke an unused invitation. Raises 404 if missing or not revocable."""
    now = _now()
    updated = _collection().find_one_and_update(
        {"invitation_id": invitation_id, "used": False, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": now}},
        return_document=True,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or cannot be revoked",
        )
    return updated


def validate_invitation(token: str, email: str) -> dict:
    """Validate an invitation token for the given email (peek, no consumption)."""
    document = _collection().find_one({"token_hash": _hash_token(token)})
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invitation"
        )
    now = _now()
    if document.get("used"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been used",
        )
    if document.get("revoked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has been revoked",
        )
    expires_at = _as_utc(document.get("expires_at"))
    if expires_at is not None and expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired",
        )
    if document.get("email") and document["email"].lower() != (email or "").lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation email does not match",
        )
    return document


def consume_invitation(invitation_id: str) -> dict:
    """Atomically consume an invitation; raises 400 if it is no longer valid."""
    now = _now()
    consumed = _collection().find_one_and_update(
        {
            "invitation_id": invitation_id,
            "used": False,
            "revoked": False,
            "expires_at": {"$gt": now},
        },
        {"$set": {"used": True, "used_at": now}},
        return_document=True,
    )
    if consumed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation is no longer valid",
        )
    return consumed
