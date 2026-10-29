"""Faculty document and profile API schemas."""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import MongoDocument, utcnow


class Faculty(MongoDocument):
    faculty_id: Optional[str] = None
    employee_id: Optional[str] = None
    name: str
    email: str
    department_id: Optional[str] = None
    designation: Optional[str] = None
    orcid_id: Optional[str] = None
    scopus_author_id: Optional[str] = None
    web_of_science_researcher_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    research_interests: Optional[list[str]] = None
    profile_photo_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)


class FacultyProfileResponse(BaseModel):
    """Public faculty profile returned by the profile endpoints.

    Contains no password, password_hash, or authentication details.
    """

    faculty_id: str
    employee_id: Optional[str] = None
    name: str
    email: str
    department_id: Optional[str] = None
    designation: Optional[str] = None
    orcid_id: Optional[str] = None
    scopus_author_id: Optional[str] = None
    web_of_science_researcher_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    research_interests: list[str] = Field(default_factory=list)
    profile_photo_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FacultyProfileUpdateRequest(BaseModel):
    """Fields a faculty member is allowed to update on their own profile.

    Protected fields (faculty_id, employee_id, email, is_active, role,
    created_at, updated_at) are intentionally absent.
    """

    name: Optional[str] = None
    department_id: Optional[str] = None
    designation: Optional[str] = None
    orcid_id: Optional[str] = None
    scopus_author_id: Optional[str] = None
    web_of_science_researcher_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    research_interests: Optional[list[str]] = None
    profile_photo_url: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value

    @field_validator(
        "department_id",
        "designation",
        "orcid_id",
        "scopus_author_id",
        "web_of_science_researcher_id",
        "pubmed_id",
        mode="before",
    )
    @classmethod
    def _strip_optional_strings(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("research_interests", mode="before")
    @classmethod
    def _clean_interests(cls, value):
        if value is None:
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped and stripped not in seen:
                    cleaned.append(stripped)
                    seen.add(stripped)
        return cleaned

    @field_validator("profile_photo_url", mode="before")
    @classmethod
    def _validate_photo_url(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            parsed = urlparse(value)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError("profile_photo_url must be a valid http(s) URL")
        return value
