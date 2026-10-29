"""Academic-year read routes for authenticated users.

The points endpoints require a real ``academic_year_id`` (they raise 404 for
unknown ids), so faculty need a read-only way to discover the available
years. Administrative management stays behind ``/api/admin/academic-years``.
"""

from fastapi import APIRouter, Depends

from app.routes import dependencies
from app.schemas.admin import AcademicYearResponse
from app.services import academic_year_service

router = APIRouter(prefix="/api/academic-years", tags=["academic-years"])


@router.get("", response_model=list[AcademicYearResponse])
async def list_academic_years(
    user: dict = Depends(dependencies.require_authenticated_user),
) -> list[AcademicYearResponse]:
    years = academic_year_service.list_academic_years()
    return [AcademicYearResponse.model_validate(year) for year in years]
