"""Admin summary route."""

from fastapi import APIRouter, Depends

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, FACULTY, PUBLICATIONS, USERS
from app.routes import dependencies
from app.schemas.admin import AdminSummaryResponse

router = APIRouter(prefix="/api/admin", tags=["admin: summary"])


@router.get("/summary", response_model=AdminSummaryResponse)
async def admin_summary(
    admin: dict = Depends(dependencies.require_admin),
) -> AdminSummaryResponse:
    faculty_collection = mongodb.get_collection(FACULTY)
    publications_collection = mongodb.get_collection(PUBLICATIONS)
    years_collection = mongodb.get_collection(ACADEMIC_YEARS)
    users_collection = mongodb.get_collection(USERS)

    current_year = years_collection.find_one({"is_current": True})

    return AdminSummaryResponse(
        faculty_count=faculty_collection.count_documents({}),
        active_faculty_count=faculty_collection.count_documents({"is_active": True}),
        publication_count=publications_collection.count_documents({}),
        pending_verification_count=publications_collection.count_documents(
            {"verification_status": "pending"}
        ),
        academic_year_count=years_collection.count_documents({}),
        current_academic_year=current_year["name"] if current_year else None,
        pending_registration_count=users_collection.count_documents(
            {"role": "faculty", "approval_status": "pending"}
        ),
    )
