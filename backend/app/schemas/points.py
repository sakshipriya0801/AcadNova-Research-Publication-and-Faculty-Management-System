"""Points API request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CategoryPoints(BaseModel):
    research_publication: int = 0
    book: int = 0
    conference: int = 0
    patent: int = 0
    copyright: int = 0
    project: int = 0
    other: int = 0


class EligibilityResult(BaseModel):
    eligible: bool
    required_points: Optional[int] = None
    total_points: int = 0
    remaining_points: Optional[int] = None
    designation: Optional[str] = None
    reason: Optional[str] = None


class PointsSummaryResponse(BaseModel):
    faculty_id: str
    academic_year_id: str
    total_points: int
    category_points: CategoryPoints
    eligibility: EligibilityResult


class RecalculateRequest(BaseModel):
    academic_year_id: str


class PublicationPointsItem(BaseModel):
    publication_id: str
    title: Optional[str] = None
    publication_type: Optional[str] = None
    publication_date: Optional[datetime] = None
    points: int = 0
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None
    reason: Optional[str] = None
