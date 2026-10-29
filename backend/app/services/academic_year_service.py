"""Academic-year helpers and admin management.

The academic year runs from 1 July to 30 June.  A publication dated
2025-08-15 belongs to academic year ``2025-2026``.
"""

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, FACULTY_POINTS, PUBLICATIONS
from app.utils.dates import to_iso_string


def academic_year_name_for_date(publication_date: date) -> str:
    """Return the academic-year name (e.g. "2025-2026") for a date."""
    if publication_date.month >= 7:
        start_year = publication_date.year
    else:
        start_year = publication_date.year - 1
    return f"{start_year}-{start_year + 1}"


def find_academic_year_by_name(name: str) -> Optional[dict]:
    return mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": name})


def resolve_academic_year(publication_date: date) -> dict:
    """Return the academic-year document for a publication date.

    Raises a clear error if the academic year has not been created yet; it is
    never created automatically.
    """
    name = academic_year_name_for_date(publication_date)
    academic_year = find_academic_year_by_name(name)
    if academic_year is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Academic year '{name}' does not exist. "
                "Please ask an administrator to create it."
            ),
        )
    return academic_year


# --- Admin management ---------------------------------------------------------


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _validate_academic_year(name: str, start_date, end_date) -> None:
    start = _as_date(start_date)
    end = _as_date(end_date)

    if start >= end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start_date must be before end_date")
    if start.month != 7 or start.day != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Academic year must start on 1 July")
    if end.month != 6 or end.day != 30:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Academic year must end on 30 June")
    if end.year != start.year + 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Academic year must span one year (1 July to 30 June)")

    expected = f"{start.year}-{start.year + 1}"
    if name != expected:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Academic year name must be '{expected}' for the given dates",
        )


def _collection():
    return mongodb.get_collection(ACADEMIC_YEARS)


def create_academic_year(name: str, start_date, end_date) -> dict:
    _validate_academic_year(name, start_date, end_date)
    if _collection().find_one({"name": name}):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Academic year '{name}' already exists"
        )

    now = datetime.now(timezone.utc)
    doc = {
        "academic_year_id": str(uuid4()),
        "name": name,
        "start_date": to_iso_string(start_date),
        "end_date": to_iso_string(end_date),
        "is_current": False,
        "created_at": now,
        "updated_at": now,
    }
    _collection().insert_one(doc)
    return doc


def list_academic_years() -> list[dict]:
    return list(_collection().find({}).sort("name", 1))


def get_academic_year(academic_year_id: str) -> Optional[dict]:
    return _collection().find_one({"academic_year_id": academic_year_id})


def update_academic_year(academic_year_id: str, fields: dict) -> dict:
    existing = get_academic_year(academic_year_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Academic year not found")

    name = fields.get("name", existing.get("name"))
    start_date = fields.get("start_date", existing.get("start_date"))
    end_date = fields.get("end_date", existing.get("end_date"))
    _validate_academic_year(name, start_date, end_date)

    if name != existing.get("name") and _collection().find_one(
        {"name": name, "academic_year_id": {"$ne": academic_year_id}}
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Academic year '{name}' already exists"
        )

    update = {
        "name": name,
        "start_date": to_iso_string(start_date),
        "end_date": to_iso_string(end_date),
        "updated_at": datetime.now(timezone.utc),
    }
    return _collection().find_one_and_update(
        {"academic_year_id": academic_year_id},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )


def set_current_academic_year(academic_year_id: str) -> dict:
    existing = get_academic_year(academic_year_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Academic year not found")

    _collection().update_many(
        {"academic_year_id": {"$ne": academic_year_id}}, {"$set": {"is_current": False}}
    )
    return _collection().find_one_and_update(
        {"academic_year_id": academic_year_id},
        {"$set": {"is_current": True, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )


def delete_academic_year(academic_year_id: str) -> None:
    existing = get_academic_year(academic_year_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Academic year not found")

    publication_count = mongodb.get_collection(PUBLICATIONS).count_documents(
        {"academic_year_id": academic_year_id}
    )
    if publication_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot delete academic year: {publication_count} publication(s) depend on it",
        )

    points_count = mongodb.get_collection(FACULTY_POINTS).count_documents(
        {"academic_year_id": academic_year_id}
    )
    if points_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot delete academic year: {points_count} faculty points record(s) depend on it",
        )

    _collection().delete_one({"academic_year_id": academic_year_id})
