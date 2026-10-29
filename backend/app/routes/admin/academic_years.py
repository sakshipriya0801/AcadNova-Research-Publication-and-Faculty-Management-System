"""Admin academic-year routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin import (
    AcademicYearCreate,
    AcademicYearResponse,
    AcademicYearUpdate,
)
from app.services import academic_year_service

router = APIRouter(prefix="/api/admin/academic-years", tags=["admin: academic-years"])


@router.post("", response_model=AcademicYearResponse, status_code=status.HTTP_201_CREATED)
async def create_academic_year(
    request: AcademicYearCreate,
    admin: dict = Depends(dependencies.require_admin),
) -> AcademicYearResponse:
    year = academic_year_service.create_academic_year(
        request.name, request.start_date, request.end_date
    )
    _audit.log(admin, "create", "academic_year", year["academic_year_id"], new_value=year)
    return AcademicYearResponse.model_validate(year)


@router.get("", response_model=list[AcademicYearResponse])
async def list_academic_years(
    admin: dict = Depends(dependencies.require_admin),
) -> list[AcademicYearResponse]:
    years = academic_year_service.list_academic_years()
    return [AcademicYearResponse.model_validate(y) for y in years]


@router.get("/{academic_year_id}", response_model=AcademicYearResponse)
async def get_academic_year(
    academic_year_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> AcademicYearResponse:
    year = academic_year_service.get_academic_year(academic_year_id)
    if year is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Academic year not found")
    return AcademicYearResponse.model_validate(year)


@router.put("/{academic_year_id}", response_model=AcademicYearResponse)
async def update_academic_year(
    academic_year_id: str,
    request: AcademicYearUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> AcademicYearResponse:
    year = academic_year_service.update_academic_year(
        academic_year_id, request.model_dump(exclude_unset=True)
    )
    _audit.log(admin, "update", "academic_year", academic_year_id, new_value=year)
    return AcademicYearResponse.model_validate(year)


@router.patch("/{academic_year_id}/current", response_model=AcademicYearResponse)
async def set_current_academic_year(
    academic_year_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> AcademicYearResponse:
    year = academic_year_service.set_current_academic_year(academic_year_id)
    _audit.log(admin, "set_current", "academic_year", academic_year_id, new_value=year)
    return AcademicYearResponse.model_validate(year)


@router.delete("/{academic_year_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_academic_year(
    academic_year_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> None:
    academic_year_service.delete_academic_year(academic_year_id)
    _audit.log(admin, "delete", "academic_year", academic_year_id)
    return None
