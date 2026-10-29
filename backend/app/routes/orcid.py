"""ORCID integration routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routes import dependencies
from app.schemas.external_publication import ExternalPublicationResult, ExternalSearchResponse
from app.schemas.orcid import OrcidProfileResponse, OrcidResearcherSearchResponse
from app.services import faculty_service, orcid_service

router = APIRouter(prefix="/api/orcid", tags=["orcid"])


def _get_faculty(user: dict) -> dict:
    faculty_id = user.get("faculty_id")
    if not faculty_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "User is not linked to a faculty profile"
        )
    faculty = faculty_service.get_faculty_profile(faculty_id)
    if faculty is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty not found")
    return faculty


@router.get("/profile", response_model=OrcidProfileResponse)
async def orcid_profile(
    user: dict = Depends(dependencies.require_authenticated_user),
) -> OrcidProfileResponse:
    return orcid_service.get_profile(_get_faculty(user))


@router.get("/works", response_model=ExternalSearchResponse)
async def orcid_works(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalSearchResponse:
    result = orcid_service.get_works(_get_faculty(user), page, page_size)
    return ExternalSearchResponse(
        source="orcid",
        page=page,
        page_size=page_size,
        total=result["total"],
        results=result["results"],
    )


@router.get("/search", response_model=OrcidResearcherSearchResponse)
async def orcid_search(
    query: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> OrcidResearcherSearchResponse:
    if not query.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "query must not be empty")
    result = orcid_service.search_researchers(query, page, page_size)
    return OrcidResearcherSearchResponse(
        query=query,
        page=page,
        page_size=page_size,
        total=result["total"],
        results=result["results"],
    )


@router.get("/researcher/{orcid_id}", response_model=OrcidProfileResponse)
async def orcid_researcher(
    orcid_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> OrcidProfileResponse:
    return orcid_service.get_researcher(orcid_id)


@router.get("/works/{work_id}", response_model=ExternalPublicationResult)
async def orcid_work(
    work_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalPublicationResult:
    return orcid_service.get_work(_get_faculty(user), work_id)
