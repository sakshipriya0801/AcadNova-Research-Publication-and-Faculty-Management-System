"""User document schema.

Only the bcrypt ``password_hash`` is stored; the plain-text password is never
persisted or returned by any endpoint.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.enums import UserRole
from app.schemas.common import MongoDocument, utcnow


class User(MongoDocument):
    user_id: Optional[str] = None
    email: str
    password_hash: Optional[str] = None
    role: UserRole = UserRole.FACULTY
    faculty_id: Optional[str] = None
    is_active: bool = True
    approval_status: str = "approved"
    rejection_reason: Optional[str] = None
    must_change_password: bool = False
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)
