"""Academic year document schema."""

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import MongoDocument, utcnow


class AcademicYear(MongoDocument):
    academic_year_id: Optional[str] = None
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)
