"""External publication integration schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ExternalAuthor(BaseModel):
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email: Optional[str] = None
    affiliation: Optional[list[str]] = None
    author_position: Optional[int] = None
    orcid_id: Optional[str] = None
    scopus_author_id: Optional[str] = None
    web_of_science_researcher_id: Optional[str] = None


class ExternalPublicationResult(BaseModel):
    source: str
    source_record_id: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: list[ExternalAuthor] = Field(default_factory=list)
    journal: Optional[str] = None
    conference: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    publication_year: Optional[int] = None
    url: Optional[str] = None
    indexing: list[str] = Field(default_factory=list)
    external_identifiers: dict[str, str] = Field(default_factory=dict)
    raw_metadata: Optional[dict] = None


class ExternalSearchResponse(BaseModel):
    source: str
    page: int
    page_size: int
    total: int
    results: list[ExternalPublicationResult]


class ExternalPublicationImportRequest(BaseModel):
    source: Literal["crossref", "pubmed", "orcid", "scopus", "web_of_science"]
    source_record_id: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    authors: list[ExternalAuthor] = Field(default_factory=list)
    journal: Optional[str] = None
    conference: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    publication_date: Optional[str] = None
    publication_year: Optional[int] = None
    url: Optional[str] = None
    indexing: list[str] = Field(default_factory=list)
    external_identifiers: dict[str, str] = Field(default_factory=dict)
    academic_year_id: Optional[str] = None
    author_match_confirmed: bool = False

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("title cannot be empty")
        return value
