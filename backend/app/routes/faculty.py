"""Faculty profile routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.schemas.faculty import FacultyProfileResponse, FacultyProfileUpdateRequest
from app.services import faculty_service

router = APIRouter(prefix="/api/faculty", tags=["faculty"])


def _get_faculty_id(user: dict) -> str:
    """Return the authenticated user's faculty_id or raise 404."""
    faculty_id = user.get("faculty_id")
    if not faculty_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found",
        )
    return faculty_id


@router.get("/profile", response_model=FacultyProfileResponse)
async def get_profile(
    user: dict = Depends(dependencies.require_authenticated_user),
) -> FacultyProfileResponse:
    """Return the profile of the currently authenticated faculty member."""
    faculty_id = _get_faculty_id(user)
    faculty = faculty_service.get_faculty_profile(faculty_id)
    if faculty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found",
        )
    return FacultyProfileResponse.model_validate(faculty)


@router.put("/profile", response_model=FacultyProfileResponse)
async def update_profile(
    request: FacultyProfileUpdateRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> FacultyProfileResponse:
    """Update the authenticated faculty member's own profile."""
    faculty_id = _get_faculty_id(user)
    updated = faculty_service.update_faculty_profile(
        faculty_id, request.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found",
        )
    return FacultyProfileResponse.model_validate(updated)
