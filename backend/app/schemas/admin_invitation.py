"""Administrator invitation and admin-registration schemas.

The raw invitation token is returned only once at creation time.  Responses for
listing never include the token or its hash.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminInvitationCreateRequest(BaseModel):
    email: EmailStr
    expires_in_hours: Optional[int] = Field(default=None, ge=1, le=168)

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: EmailStr) -> str:
        return value.lower()


class AdminInvitationCreateResponse(BaseModel):
    invitation_id: str
    email: str
    status: str = "pending"
    expires_at: datetime
    created_at: datetime
    # Raw token — returned exactly once so the administrator can share the link.
    token: str


class AdminInvitationResponse(BaseModel):
    invitation_id: str
    email: str
    status: str
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class AdminInvitationListResponse(BaseModel):
    items: list[AdminInvitationResponse] = Field(default_factory=list)
    total: int = 0


class AdminRegisterRequest(BaseModel):
    token: str = Field(..., min_length=8)
    name: Optional[str] = None
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")
        return value
