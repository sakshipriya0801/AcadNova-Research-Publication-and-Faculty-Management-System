"""Publication management routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.enums import PublicationSource, PublicationType, VerificationStatus
from app.routes import dependencies
from app.schemas.external_publication import (
    ExternalPublicationImportRequest,
    ExternalPublicationResult,
    ExternalSearchResponse,
)
from app.schemas.publication import (
    PublicationCreateRequest,
    PublicationListResponse,
    PublicationResponse,
    PublicationUpdateRequest,
)
from app.schemas.verification_record import (
    VerificationRecordResponse,
    verification_record_response,
)
from app.services import (
    external_publication_service,
    publication_service,
    verification_service,
)

router = APIRouter(prefix="/api/publications", tags=["publications"])


def _get_faculty_id(user: dict) -> str:
    faculty_id = user.get("faculty_id")
    if not faculty_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not linked to a faculty profile",
        )
    return faculty_id


@router.post("", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
async def create_publication(
    request: PublicationCreateRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PublicationResponse:
    faculty_id = _get_faculty_id(user)
    publication = publication_service.create_publication(
        faculty_id, request.model_dump()
    )
    return PublicationResponse.model_validate(publication)


@router.get("", response_model=PublicationListResponse)
async def list_publications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    publication_type: Optional[PublicationType] = None,
    verification_status: Optional[VerificationStatus] = None,
    publication_year: Optional[int] = None,
    academic_year_id: Optional[str] = None,
    source: Optional[PublicationSource] = None,
    indexing: Optional[str] = None,
    sort_by: str = Query("publication_date"),
    sort_order: str = Query("desc"),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PublicationListResponse:
    faculty_id = _get_faculty_id(user)
    result = publication_service.list_publications(
        faculty_id=faculty_id,
        page=page,
        page_size=page_size,
        search=search,
        publication_type=publication_type.value if publication_type else None,
        verification_status=(
            verification_status.value if verification_status else None
        ),
        publication_year=publication_year,
        academic_year_id=academic_year_id,
        source=source.value if source else None,
        indexing=indexing,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PublicationListResponse(
        items=[PublicationResponse.model_validate(item) for item in result["items"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    )


@router.get("/search-external", response_model=ExternalSearchResponse)
async def search_external_publications(
    source: str,
    query: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    author: Optional[str] = None,
    title: Optional[str] = None,
    doi: Optional[str] = None,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalSearchResponse:
    if not any([query.strip(), author, title, doi]):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "query must not be empty"
        )
    result = external_publication_service.search_external(
        source=source,
        query=query,
        page=page,
        page_size=page_size,
        author=author,
        title=title,
        doi=doi,
    )
    return ExternalSearchResponse(**result)


@router.get("/external/{source}/{record_id:path}", response_model=ExternalPublicationResult)
async def get_external_record(
    source: str,
    record_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalPublicationResult:
    return external_publication_service.get_external_record(source, record_id)


@router.post(
    "/import-external",
    response_model=PublicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_external_publication(
    request: ExternalPublicationImportRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PublicationResponse:
    faculty_id = _get_faculty_id(user)
    publication = external_publication_service.import_external_publication(
        faculty_id, request.model_dump()
    )
    return PublicationResponse.model_validate(publication)


@router.get("/{publication_id}", response_model=PublicationResponse)
async def get_publication(
    publication_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PublicationResponse:
    faculty_id = _get_faculty_id(user)
    publication = publication_service.get_publication_by_id(
        publication_id, faculty_id
    )
    return PublicationResponse.model_validate(publication)


@router.put("/{publication_id}", response_model=PublicationResponse)
async def update_publication(
    publication_id: str,
    request: PublicationUpdateRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> PublicationResponse:
    faculty_id = _get_faculty_id(user)
    updated = publication_service.update_publication(
        publication_id, faculty_id, request.model_dump(exclude_unset=True)
    )
    return PublicationResponse.model_validate(updated)


@router.delete("/{publication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publication(
    publication_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> None:
    faculty_id = _get_faculty_id(user)
    publication_service.delete_publication(publication_id, faculty_id)
    return None


@router.get(
    "/{publication_id}/verification-history",
    response_model=list[VerificationRecordResponse],
)
async def publication_verification_history(
    publication_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> list[VerificationRecordResponse]:
    faculty_id = _get_faculty_id(user)
    publication = publication_service.find_publication_by_id(publication_id)
    if publication is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publication not found")
    if publication.get("faculty_id") != faculty_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only view the verification history of your own publications",
        )
    records = verification_service.get_verification_history(publication_id)
    return [verification_record_response(r) for r in records]
