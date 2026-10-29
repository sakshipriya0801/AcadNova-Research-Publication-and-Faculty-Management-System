"""Administrator account management.

Creating administrators is restricted to authenticated administrators at the
route layer (``require_admin``).  Passwords are hashed with the project's
password hashing utility and never stored or returned in plain text.  The role
is always forced to ``admin`` for accounts created here and existing accounts
(e.g. faculty) are never promoted.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.database import mongodb
from app.models.collections import USERS
from app.models.enums import UserRole
from app.services import user_service
from app.utils import security


def list_admins() -> list[dict]:
    """Return administrator accounts (no credential fields)."""
    return list(
        mongodb.get_collection(USERS)
        .find({"role": UserRole.ADMIN.value}, {"_id": 0})
        .sort("created_at", 1)
    )


def create_admin(email: str, password: str, name: Optional[str] = None) -> dict:
    """Create a new administrator account.

    Raises HTTPException(409) if the email is already registered (regardless of
    the existing account's role), so a request can never promote an existing
    user.
    """
    if user_service.find_user_by_email(email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    now = datetime.now(timezone.utc)
    document = {
        "user_id": str(uuid4()),
        "email": email,
        "name": name,
        "password_hash": security.hash_password(password),
        "role": UserRole.ADMIN.value,
        "faculty_id": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    try:
        user_service.create_user(document)
    except DuplicateKeyError:
        # Concurrency: another request created this email first.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    return document