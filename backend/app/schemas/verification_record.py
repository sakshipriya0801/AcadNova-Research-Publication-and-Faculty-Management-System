"""Verification record schema and verification request/response schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import MongoDocument, utcnow
from app.schemas.publication import PublicationResponse


class VerificationRecord(MongoDocument):
    """A single verification action performed on a publication."""

    verification_id: Optional[str] = None
    publication_id: str
    faculty_id: Optional[str] = None
    verified_by_user_id: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=utcnow)


class VerificationRequest(BaseModel):
    action: Literal["verify", "reject"]
    reason: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("reason", "notes", mode="before")
    @classmethod
    def _strip_optional(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class VerificationRecordResponse(BaseModel):
    id: str
    publication_id: str
    faculty_id: Optional[str] = None
    verified_by_user_id: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class PublicationVerificationResponse(BaseModel):
    publication: PublicationResponse
    verification: VerificationRecordResponse


def verification_record_response(record: dict) -> VerificationRecordResponse:
    """Map a stored verification record to its API representation."""
    return VerificationRecordResponse(
        id=record.get("verification_id"),
        publication_id=record.get("publication_id"),
        faculty_id=record.get("faculty_id"),
        verified_by_user_id=record.get("verified_by_user_id"),
        previous_status=record.get("previous_status"),
        new_status=record.get("new_status"),
        action=record.get("action"),
        reason=record.get("reason"),
        notes=record.get("notes"),
        created_at=record.get("created_at"),
    )
