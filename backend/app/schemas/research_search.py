"""Unified research publication search schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResearchSearchResult(BaseModel):
    kind: Literal["internal", "external"]
    source: Optional[str] = None
    source_record_id: Optional[str] = None
    publication_id: Optional[str] = None
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    publication_date: Optional[str] = None
    publication_year: Optional[int] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    indexing: list[str] = Field(default_factory=list)
    external_identifiers: dict[str, str] = Field(default_factory=dict)
    verification_status: Optional[str] = None
    faculty_id: Optional[str] = None
    faculty_name: Optional[str] = None
    importable: bool = False


class ResearchSearchResponse(BaseModel):
    type: str
    query: str
    page: int
    page_size: int
    total: int
    results: list[ResearchSearchResult] = Field(default_factory=list)
