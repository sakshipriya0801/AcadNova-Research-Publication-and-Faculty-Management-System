"""Faculty points document schema (per faculty per academic year)."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import MongoDocument, utcnow


class FacultyPoints(MongoDocument):
    faculty_points_id: Optional[str] = None
    faculty_id: str
    academic_year_id: str
    total_points: int = 0
    research_publication_points: int = 0
    book_points: int = 0
    conference_points: int = 0
    patent_points: int = 0
    copyright_points: int = 0
    project_points: int = 0
    other_points: int = 0
    last_calculated_at: Optional[datetime] = None
