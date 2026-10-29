"""Points and eligibility routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.schemas.points import (
    PointsSummaryResponse,
    PublicationPointsItem,
    RecalculateRequest,
)
from app.services import points_service

router = APIRouter(prefix="/api/points", tags=["points"])


def _get_faculty_id(user: dict) -> str:
    faculty_id = user.get("faculty_id")
    if not faculty_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a faculty profile",
        )
    return faculty_id


@router.get("/summary", response_model=PointsSummaryResponse)
async def points_summary(
    academic_year_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PointsSummaryResponse:
    faculty_id = _get_faculty_id(user)
    return points_service.get_points_summary(faculty_id, academic_year_id)


@router.post("/recalculate", response_model=PointsSummaryResponse)
async def recalculate_points(
    request: RecalculateRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PointsSummaryResponse:
    faculty_id = _get_faculty_id(user)
    return points_service.recalculate_points(faculty_id, request.academic_year_id)


@router.get("/breakdown", response_model=list[PublicationPointsItem])
async def points_breakdown(
    academic_year_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> list[PublicationPointsItem]:
    faculty_id = _get_faculty_id(user)
    return points_service.get_points_breakdown(faculty_id, academic_year_id)
