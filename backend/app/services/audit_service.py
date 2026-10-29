"""Reusable audit logging (``audit_logs`` collection).

Never stores passwords or secrets.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from bson import ObjectId

from app.database import mongodb
from app.models.collections import AUDIT_LOGS


def log_audit(
    user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    old_value: Optional[dict[str, Any]] = None,
    new_value: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Insert an audit-log entry and return it."""
    doc = {
        "audit_id": str(uuid4()),
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "old_value": old_value,
        "new_value": new_value,
        "timestamp": datetime.now(timezone.utc),
        "ip_address": ip_address,
    }
    mongodb.get_collection(AUDIT_LOGS).insert_one(doc)
    return doc


def _sanitize(value: Any) -> Any:
    """Make stored values JSON-safe and drop Mongo internals (``_id``)."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not key.startswith("_")
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def list_audit_logs(
    page: int = 1,
    page_size: int = 25,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> dict:
    """Return a newest-first page of audit-log entries for the admin console."""
    query: dict = {}
    if action:
        query["action"] = action
    if entity_type:
        query["entity_type"] = entity_type

    collection = mongodb.get_collection(AUDIT_LOGS)
    total = collection.count_documents(query)
    skip = (max(1, page) - 1) * page_size
    cursor = (
        collection.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(page_size)
    )
    items = []
    for record in cursor:
        record.pop("_id", None)
        record["old_value"] = _sanitize(record.get("old_value"))
        record["new_value"] = _sanitize(record.get("new_value"))
        items.append(record)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }
