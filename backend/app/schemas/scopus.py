"""Scopus integration schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class ScopusAuthorResponse(BaseModel):
    author_id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    affiliations: list[str] = Field(default_factory=list)
    subject_areas: list[str] = Field(default_factory=list)
