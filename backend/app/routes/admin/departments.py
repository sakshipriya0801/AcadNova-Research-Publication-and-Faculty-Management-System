"""Admin department routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services import department_service

router = APIRouter(prefix="/api/admin/departments", tags=["admin: departments"])


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    request: DepartmentCreate,
    admin: dict = Depends(dependencies.require_admin),
) -> DepartmentResponse:
    department = department_service.create_department(
        request.name, request.code, request.description
    )
    _audit.log(
        admin, "create", "department", department["department_id"], new_value=department
    )
    return DepartmentResponse.model_validate(department)


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    admin: dict = Depends(dependencies.require_admin),
) -> list[DepartmentResponse]:
    departments = department_service.list_departments()
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> DepartmentResponse:
    department = department_service.get_department(department_id)
    if department is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")
    return DepartmentResponse.model_validate(department)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: str,
    request: DepartmentUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> DepartmentResponse:
    department = department_service.update_department(
        department_id, request.model_dump(exclude_unset=True)
    )
    _audit.log(admin, "update", "department", department_id, new_value=department)
    return DepartmentResponse.model_validate(department)


@router.patch("/{department_id}/deactivate", response_model=DepartmentResponse)
async def deactivate_department(
    department_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> DepartmentResponse:
    department = department_service.deactivate_department(department_id)
    _audit.log(admin, "deactivate", "department", department_id)
    return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> None:
    department_service.delete_department(department_id)
    _audit.log(admin, "delete", "department", department_id)
    return None
