"""Department document schema."""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import MongoDocument, utcnow


class Department(MongoDocument):
    department_id: Optional[str] = None
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)
