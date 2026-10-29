"""Eligibility rule document schema.

Eligibility rules map a faculty designation to the minimum points required for
annual increment eligibility.  These thresholds are stored in the database so
they can be changed without modifying code.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import MongoDocument, utcnow


class EligibilityRule(MongoDocument):
    eligibility_rule_id: Optional[str] = None
    code: Optional[str] = None
    designation: str
    minimum_points: int = 0
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)
