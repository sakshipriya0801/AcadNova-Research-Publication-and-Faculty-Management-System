"""Department admin operations (``departments`` collection)."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.database import mongodb
from app.models.collections import DEPARTMENTS, FACULTY


def _collection():
    return mongodb.get_collection(DEPARTMENTS)


def _find_by_code(code: str, exclude_id: Optional[str] = None):
    query: dict = {"code": code}
    if exclude_id:
        query["department_id"] = {"$ne": exclude_id}
    return _collection().find_one(query)


def create_department(
    name: str, code: Optional[str] = None, description: Optional[str] = None
) -> dict:
    if code and _find_by_code(code):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Department code '{code}' already exists"
        )
    now = datetime.now(timezone.utc)
    doc = {
        "department_id": str(uuid4()),
        "name": name,
        "code": code,
        "description": description,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    _collection().insert_one(doc)
    return doc


def list_departments() -> list[dict]:
    return list(_collection().find({}).sort("name", 1))


def get_department(department_id: str) -> Optional[dict]:
    return _collection().find_one({"department_id": department_id})


def update_department(department_id: str, fields: dict) -> dict:
    existing = get_department(department_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")

    code = fields.get("code", existing.get("code"))
    if code and _find_by_code(code, exclude_id=department_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Department code '{code}' already exists"
        )

    fields["updated_at"] = datetime.now(timezone.utc)
    return _collection().find_one_and_update(
        {"department_id": department_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )


def deactivate_department(department_id: str) -> dict:
    return update_department(department_id, {"is_active": False})


def delete_department(department_id: str) -> None:
    existing = get_department(department_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")

    faculty_count = mongodb.get_collection(FACULTY).count_documents(
        {"department_id": department_id}
    )
    if faculty_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot delete department: {faculty_count} faculty member(s) use it. Deactivate it instead.",
        )

    _collection().delete_one({"department_id": department_id})
