"""Admin audit-log response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    audit_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: Optional[datetime] = None
    ip_address: Optional[str] = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse] = Field(default_factory=list)
    page: int = 1
    page_size: int = 25
    total: int = 0
    total_pages: int = 0
