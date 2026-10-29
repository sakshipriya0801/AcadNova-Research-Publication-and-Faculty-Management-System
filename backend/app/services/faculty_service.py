"""Faculty database operations (``faculty`` collection)."""

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.database import mongodb
from app.models.collections import FACULTY
from app.services import user_service

# Fields a faculty member may update on their own profile. Everything else
# (faculty_id, employee_id, email, is_active, role, timestamps) is protected.
ALLOWED_PROFILE_FIELDS = {
    "name",
    "department_id",
    "designation",
    "orcid_id",
    "scopus_author_id",
    "web_of_science_researcher_id",
    "pubmed_id",
    "research_interests",
    "profile_photo_url",
}


def _collection():
    return mongodb.get_collection(FACULTY)


def find_faculty_by_email(email: str) -> Optional[dict]:
    return _collection().find_one({"email": email})


def find_faculty_by_employee_id(employee_id: str) -> Optional[dict]:
    return _collection().find_one({"employee_id": employee_id})


def find_faculty_by_id(faculty_id: str) -> Optional[dict]:
    return _collection().find_one({"faculty_id": faculty_id})


def create_faculty(faculty_data: dict) -> dict:
    """Insert a new faculty document and return it."""
    now = datetime.now(timezone.utc)
    faculty_data.setdefault("faculty_id", str(uuid4()))
    faculty_data.setdefault("is_active", True)
    faculty_data.setdefault("created_at", now)
    faculty_data.setdefault("updated_at", now)
    _collection().insert_one(faculty_data)
    return faculty_data


def get_faculty_profile(faculty_id: str) -> Optional[dict]:
    """Return the faculty document for the given faculty_id, or None."""
    return _collection().find_one({"faculty_id": faculty_id})


def update_faculty_profile(faculty_id: str, update_fields: dict) -> Optional[dict]:
    """Update only allowed profile fields and return the updated document.

    ``update_fields`` is filtered against ``ALLOWED_PROFILE_FIELDS`` so that
    protected fields can never be changed through this path.  ``updated_at``
    is refreshed automatically.
    """
    fields = {k: v for k, v in update_fields.items() if k in ALLOWED_PROFILE_FIELDS}
    if not fields:
        return get_faculty_profile(faculty_id)

    fields["updated_at"] = datetime.now(timezone.utc)
    return _collection().find_one_and_update(
        {"faculty_id": faculty_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )


# --- Admin management ---------------------------------------------------------

def list_faculty(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    department_id: Optional[str] = None,
    designation: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> dict:
    query: dict = {}
    if search:
        regex = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"employee_id": regex},
            {"email": regex},
        ]
    if department_id:
        query["department_id"] = department_id
    if designation:
        query["designation"] = designation
    if is_active is not None:
        query["is_active"] = is_active

    total = _collection().count_documents(query)
    skip = (page - 1) * page_size
    items = list(_collection().find(query).sort("name", 1).skip(skip).limit(page_size))
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


def update_faculty_admin(faculty_id: str, fields: dict) -> dict:
    existing = get_faculty_profile(faculty_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty not found")

    new_email = fields.get("email")
    if new_email is not None and new_email != existing.get("email"):
        if find_faculty_by_email(new_email) or user_service.find_user_by_email(new_email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
        user_service.update_user_by_faculty_id(faculty_id, {"email": new_email})
    elif "email" in fields:
        fields.pop("email")

    new_employee_id = fields.get("employee_id")
    if new_employee_id is not None and new_employee_id != existing.get("employee_id"):
        if find_faculty_by_employee_id(new_employee_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "Employee ID already in use")

    if not fields:
        return existing

    fields["updated_at"] = datetime.now(timezone.utc)
    return _collection().find_one_and_update(
        {"faculty_id": faculty_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )


def set_faculty_status(faculty_id: str, is_active: bool) -> dict:
    existing = get_faculty_profile(faculty_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty not found")

    fields = {"is_active": is_active, "updated_at": datetime.now(timezone.utc)}
    updated = _collection().find_one_and_update(
        {"faculty_id": faculty_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )
    user_service.update_user_by_faculty_id(faculty_id, {"is_active": is_active})
    return updated
