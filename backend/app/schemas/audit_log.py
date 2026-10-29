"""Audit log document schema.

Full audit logging is NOT implemented yet; this is only the model foundation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from app.schemas.common import MongoDocument, utcnow


class AuditLog(MongoDocument):
    audit_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    timestamp: Optional[datetime] = Field(default_factory=utcnow)
    ip_address: Optional[str] = None
