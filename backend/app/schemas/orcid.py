"""ORCID integration schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class OrcidEmployment(BaseModel):
    organization: Optional[str] = None
    department: Optional[str] = None
    role_title: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class OrcidProfileResponse(BaseModel):
    orcid_id: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    credit_name: Optional[str] = None
    biography: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    employments: list[OrcidEmployment] = Field(default_factory=list)
    researcher_identifiers: dict[str, str] = Field(default_factory=dict)


class OrcidResearcherSearchResponse(BaseModel):
    query: str
    page: int
    page_size: int
    total: int
    results: list[OrcidProfileResponse]
