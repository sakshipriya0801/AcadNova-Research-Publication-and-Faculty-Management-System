"""Publication document and API schemas.

Supports publications coming from different external sources
(``manual``, ``pubmed``, ``crossref``, ``orcid``, ``scopus``,
``web_of_science``).  Institutional points are intentionally NOT embedded in
this model; they are derived from the configurable rule engine later.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import PublicationSource, PublicationType, VerificationStatus
from app.schemas.common import MongoDocument, utcnow


class Publication(MongoDocument):
    publication_id: Optional[str] = None
    title: str
    authors: Optional[list[str]] = None
    author_count: Optional[int] = None
    faculty_id: Optional[str] = None
    faculty_author_position: Optional[int] = None
    is_corresponding_author: bool = False
    publication_type: Optional[PublicationType] = None
    journal_name: Optional[str] = None
    conference_name: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_date: Optional[date] = None
    publication_year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: Optional[list[str]] = None
    source: PublicationSource = PublicationSource.MANUAL
    source_record_id: Optional[str] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None
    indexing: Optional[list[str]] = None
    collaboration_type: Optional[str] = None
    external_institution: Optional[str] = None
    sub_type: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    points_awarded: Optional[int] = None
    academic_year_id: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)


def _clean_list(values) -> list[str]:
    """Strip whitespace, drop empty entries and de-duplicate a string list."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values or []:
        if isinstance(item, str):
            value = item.strip()
            if value and value not in seen:
                cleaned.append(value)
                seen.add(value)
    return cleaned


class PublicationCreateRequest(BaseModel):
    """Fields accepted when a faculty member creates a publication manually."""

    title: str
    authors: list[str]
    publication_type: PublicationType
    faculty_author_position: Optional[int] = Field(default=None, ge=1)
    is_corresponding_author: bool = False
    journal_name: Optional[str] = None
    conference_name: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_date: date
    abstract: Optional[str] = None
    keywords: Optional[list[str]] = None
    indexing: Optional[list[str]] = None
    collaboration_type: Optional[str] = None
    external_institution: Optional[str] = None
    sub_type: Optional[str] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("title cannot be empty")
        return value

    @field_validator("authors", mode="before")
    @classmethod
    def _validate_authors(cls, value):
        if value is None:
            return value
        cleaned = _clean_list(value)
        if not cleaned:
            raise ValueError("authors must not be empty")
        return cleaned

    @field_validator("keywords", "indexing", mode="before")
    @classmethod
    def _clean_keywords_indexing(cls, value):
        if value is None:
            return None
        return _clean_list(value)

    @field_validator(
        "journal_name", "conference_name", "publisher", "doi", "issn", "isbn",
        "volume", "issue", "pages", "collaboration_type", "external_institution",
        "source_url", "pdf_url", "sub_type", mode="before",
    )
    @classmethod
    def _strip_optional_strings(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class PublicationUpdateRequest(BaseModel):
    """Fields a faculty member may update on their own publication.

    Protected fields (publication_id, faculty_id, points_awarded,
    verification_status, source, source_record_id, author_count, timestamps)
    are intentionally absent.
    """

    title: Optional[str] = None
    authors: Optional[list[str]] = None
    publication_type: Optional[PublicationType] = None
    faculty_author_position: Optional[int] = Field(default=None, ge=1)
    is_corresponding_author: Optional[bool] = None
    journal_name: Optional[str] = None
    conference_name: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_date: Optional[date] = None
    abstract: Optional[str] = None
    keywords: Optional[list[str]] = None
    indexing: Optional[list[str]] = None
    collaboration_type: Optional[str] = None
    external_institution: Optional[str] = None
    sub_type: Optional[str] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("title cannot be empty")
        return value

    @field_validator("authors", mode="before")
    @classmethod
    def _validate_authors(cls, value):
        if value is None:
            return None
        cleaned = _clean_list(value)
        if not cleaned:
            raise ValueError("authors must not be empty")
        return cleaned

    @field_validator("keywords", "indexing", mode="before")
    @classmethod
    def _clean_keywords_indexing(cls, value):
        if value is None:
            return None
        return _clean_list(value)

    @field_validator(
        "journal_name", "conference_name", "publisher", "doi", "issn", "isbn",
        "volume", "issue", "pages", "collaboration_type", "external_institution",
        "source_url", "pdf_url", "sub_type", mode="before",
    )
    @classmethod
    def _strip_optional_strings(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class PublicationResponse(BaseModel):
    """Clean publication representation returned by the API."""

    publication_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    author_count: Optional[int] = None
    faculty_id: Optional[str] = None
    faculty_author_position: Optional[int] = None
    is_corresponding_author: bool = False
    publication_type: Optional[PublicationType] = None
    journal_name: Optional[str] = None
    conference_name: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publication_date: Optional[date] = None
    publication_year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    source: PublicationSource = PublicationSource.MANUAL
    source_record_id: Optional[str] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None
    indexing: list[str] = Field(default_factory=list)
    collaboration_type: Optional[str] = None
    external_institution: Optional[str] = None
    sub_type: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    points_awarded: int = 0
    academic_year_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("publication_date", mode="before")
    @classmethod
    def _coerce_publication_date(cls, value):
        # MongoDB returns datetimes; expose them as plain dates.
        if isinstance(value, datetime):
            return value.date()
        return value


class PublicationListResponse(BaseModel):
    """Paginated list of publications."""

    items: list[PublicationResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
