"""Department reference list for authenticated users.

Reports need a human-readable department name, but the faculty profile only
carries ``department_id`` and department management stays behind
``/api/admin/departments``. This is a minimal read-only lookup so the frontend
never has to display raw ids.
"""

from fastapi import APIRouter, Depends

from app.routes import dependencies
from app.schemas.admin import DepartmentResponse
from app.services import department_service

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    user: dict = Depends(dependencies.require_authenticated_user),
) -> list[DepartmentResponse]:
    departments = department_service.list_departments()
    return [DepartmentResponse.model_validate(d) for d in departments]
