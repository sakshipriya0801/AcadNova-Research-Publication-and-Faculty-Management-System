"""Admin faculty-management routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin import (
    FacultyAdminUpdate,
    FacultyApplicationListResponse,
    FacultyApplicationResponse,
    FacultyCreateRequest,
    FacultyCreateResponse,
    FacultyListResponse,
    FacultyRejectRequest,
    FacultyStatusUpdate,
)
from app.schemas.faculty import FacultyProfileResponse
from app.services import auth_service, faculty_approval_service, faculty_service

router = APIRouter(prefix="/api/admin/faculty", tags=["admin: faculty"])


@router.get("", response_model=FacultyListResponse)
async def list_faculty(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    department_id: Optional[str] = None,
    designation: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyListResponse:
    result = faculty_service.list_faculty(
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        designation=designation,
        is_active=is_active,
    )
    return FacultyListResponse(
        items=[FacultyProfileResponse.model_validate(f) for f in result["items"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    )


@router.post("", response_model=FacultyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_faculty(
    request: FacultyCreateRequest,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyCreateResponse:
    user, generated_password = auth_service.create_faculty_account(
        name=request.name,
        email=request.email,
        password=request.password,
        employee_id=request.employee_id,
        department_id=request.department_id,
        designation=request.designation,
    )
    faculty = faculty_service.get_faculty_profile(user["faculty_id"])
    _audit.log(
        admin,
        "create",
        "faculty",
        faculty["faculty_id"],
        new_value={"email": faculty["email"], "name": faculty["name"]},
    )
    response = FacultyProfileResponse.model_validate(faculty)
    return FacultyCreateResponse(
        **response.model_dump(),
        generated_password=generated_password,
    )


@router.get("/approvals", response_model=FacultyApplicationListResponse)
async def list_faculty_applications(
    approval_status: str = Query("pending"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyApplicationListResponse:
    result = faculty_approval_service.list_applications(
        approval_status=approval_status,
        page=page,
        page_size=page_size,
    )
    return FacultyApplicationListResponse(
        items=[FacultyApplicationResponse(**item) for item in result["items"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    )


@router.post("/{faculty_id}/approve", response_model=FacultyApplicationResponse)
async def approve_faculty(
    faculty_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyApplicationResponse:
    user = faculty_approval_service.set_approval(faculty_id, "approved")
    _audit.log(admin, "approve", "faculty_registration", faculty_id)
    faculty = faculty_service.get_faculty_profile(faculty_id) or {}
    return FacultyApplicationResponse(
        faculty_id=faculty_id,
        name=faculty.get("name"),
        email=user.get("email") or faculty.get("email"),
        employee_id=faculty.get("employee_id"),
        designation=faculty.get("designation"),
        department_id=faculty.get("department_id"),
        approval_status="approved",
        rejection_reason=None,
        created_at=faculty.get("created_at"),
    )


@router.post("/{faculty_id}/reject", response_model=FacultyApplicationResponse)
async def reject_faculty(
    faculty_id: str,
    request: FacultyRejectRequest,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyApplicationResponse:
    user = faculty_approval_service.set_approval(faculty_id, "rejected", request.reason)
    _audit.log(
        admin,
        "reject",
        "faculty_registration",
        faculty_id,
        new_value={"reason": request.reason},
    )
    faculty = faculty_service.get_faculty_profile(faculty_id) or {}
    return FacultyApplicationResponse(
        faculty_id=faculty_id,
        name=faculty.get("name"),
        email=user.get("email") or faculty.get("email"),
        employee_id=faculty.get("employee_id"),
        designation=faculty.get("designation"),
        department_id=faculty.get("department_id"),
        approval_status="rejected",
        rejection_reason=request.reason,
        created_at=faculty.get("created_at"),
    )


@router.get("/{faculty_id}", response_model=FacultyProfileResponse)
async def get_faculty(
    faculty_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyProfileResponse:
    faculty = faculty_service.get_faculty_profile(faculty_id)
    if faculty is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty not found")
    return FacultyProfileResponse.model_validate(faculty)


@router.put("/{faculty_id}", response_model=FacultyProfileResponse)
async def update_faculty(
    faculty_id: str,
    request: FacultyAdminUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyProfileResponse:
    faculty = faculty_service.update_faculty_admin(
        faculty_id, request.model_dump(exclude_unset=True)
    )
    _audit.log(admin, "update", "faculty", faculty_id, new_value=faculty)
    return FacultyProfileResponse.model_validate(faculty)


@router.patch("/{faculty_id}/status", response_model=FacultyProfileResponse)
async def update_faculty_status(
    faculty_id: str,
    request: FacultyStatusUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> FacultyProfileResponse:
    faculty = faculty_service.set_faculty_status(faculty_id, request.is_active)
    _audit.log(
        admin,
        "status",
        "faculty",
        faculty_id,
        new_value={"is_active": request.is_active},
    )
    return FacultyProfileResponse.model_validate(faculty)
