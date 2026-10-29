"""Faculty registration-approval workflow.

The authoritative approval state lives on the ``users`` document (the
authentication source of truth).  Applications are joined with the ``faculty``
collection for display; approval/rejection is idempotent and audited by the
caller.
"""

from typing import Optional

from fastapi import HTTPException, status

from app.database import mongodb
from app.models.collections import USERS
from app.services import faculty_service, user_service


def list_applications(
    approval_status: str = "pending",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Return faculty registration applications joined with faculty details."""
    collection = mongodb.get_collection(USERS)
    query: dict = {"role": "faculty"}
    if approval_status and approval_status != "all":
        query["approval_status"] = approval_status

    total = collection.count_documents(query)
    skip = (max(1, page) - 1) * page_size
    users = list(
        collection.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )

    items = []
    for user in users:
        faculty = faculty_service.get_faculty_profile(user.get("faculty_id")) or {}
        items.append(
            {
                "faculty_id": user.get("faculty_id") or faculty.get("faculty_id"),
                "name": faculty.get("name"),
                "email": user.get("email") or faculty.get("email"),
                "employee_id": faculty.get("employee_id"),
                "designation": faculty.get("designation"),
                "department_id": faculty.get("department_id"),
                "approval_status": user_service.approval_status(user),
                "rejection_reason": user.get("rejection_reason"),
                "created_at": faculty.get("created_at") or user.get("created_at"),
            }
        )

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def set_approval(
    faculty_id: str,
    new_status: str,
    reason: Optional[str] = None,
) -> dict:
    """Approve or reject a faculty registration (idempotent)."""
    user = user_service.find_user_by_faculty_id(faculty_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty not found")

    fields = {"approval_status": new_status}
    if new_status == "rejected":
        fields["rejection_reason"] = reason
    else:
        fields["rejection_reason"] = None
    user_service.update_user(user["user_id"], fields)
    return user_service.find_user_by_id(user["user_id"])
