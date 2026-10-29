"""Admin account management schemas.

Responses never include the password hash or any credential material.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminCreateRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

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


class AdminAccountResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class AdminAccountListResponse(BaseModel):
    items: list[AdminAccountResponse] = Field(default_factory=list)
    total: int = 0
