"""Publication verification workflow (``verification_records`` collection).

Only verified publications contribute official points; this module manages the
pending/verified/rejected lifecycle and records every status change.  Points
are never awarded here — the points engine remains the single source of truth.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.database import mongodb
from app.models.collections import PUBLICATIONS, VERIFICATION_RECORDS
from app.services import audit_service, points_service
from app.services.publication_service import find_publication_by_id

logger = logging.getLogger(__name__)

# Allowed verification transitions.
ALLOWED_TRANSITIONS = {
    "pending": {"verified", "rejected"},
    "verified": {"rejected"},
    "rejected": {"verified"},
}


def _records_collection():
    return mongodb.get_collection(VERIFICATION_RECORDS)


def _publications_collection():
    return mongodb.get_collection(PUBLICATIONS)


def verify_publication(
    publication_id: str,
    admin_user: dict,
    action: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> tuple[dict, dict]:
    """Apply a verification action and return (publication, record)."""
    publication = find_publication_by_id(publication_id)
    if publication is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publication not found")

    current = publication.get("verification_status", "pending")
    target = "verified" if action == "verify" else "rejected"

    if action == "reject" and not reason:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Reason is required when rejecting a publication"
        )

    if current == target:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Publication is already '{target}'"
        )

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot transition publication from '{current}' to '{target}'",
        )

    now = datetime.now(timezone.utc)
    record = {
        "verification_id": str(uuid4()),
        "publication_id": publication_id,
        "faculty_id": publication.get("faculty_id"),
        "verified_by_user_id": admin_user.get("user_id"),
        "previous_status": current,
        "new_status": target,
        "action": action,
        "reason": reason,
        "notes": notes,
        "created_at": now,
    }
    _records_collection().insert_one(record)

    updated = _publications_collection().find_one_and_update(
        {"publication_id": publication_id},
        {"$set": {"verification_status": target, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )

    audit_service.log_audit(
        user_id=admin_user.get("user_id"),
        action=f"publication.{action}",
        entity_type="publication",
        entity_id=publication_id,
        old_value={"verification_status": current},
        new_value={"verification_status": target},
    )

    _recalculate_best_effort(publication)

    return updated, record


def _recalculate_best_effort(publication: dict) -> None:
    """Refresh faculty points after a status change (best effort)."""
    faculty_id = publication.get("faculty_id")
    academic_year_id = publication.get("academic_year_id")
    if not faculty_id or not academic_year_id:
        return
    try:
        points_service.recalculate_points(faculty_id, academic_year_id)
    except Exception as exc:  # never fail verification due to recalculation
        logger.warning("Recalculation after verification failed: %s", exc)


def get_verification_history(publication_id: str) -> list[dict]:
    """Return verification records for a publication, newest first."""
    return list(
        _records_collection()
        .find({"publication_id": publication_id})
        .sort("created_at", -1)
    )
