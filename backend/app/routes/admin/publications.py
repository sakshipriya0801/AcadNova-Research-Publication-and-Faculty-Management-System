"""Admin publication review and verification routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.routes import dependencies
from app.schemas.publication import PublicationListResponse, PublicationResponse
from app.schemas.verification_record import (
    PublicationVerificationResponse,
    VerificationRecordResponse,
    VerificationRequest,
    verification_record_response,
)
from app.services import publication_service, verification_service

router = APIRouter(prefix="/api/admin/publications", tags=["admin: publications"])


@router.get("", response_model=PublicationListResponse)
async def list_publications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    verification_status: Optional[str] = None,
    publication_type: Optional[str] = None,
    publication_year: Optional[int] = None,
    academic_year_id: Optional[str] = None,
    source: Optional[str] = None,
    indexing: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    admin: dict = Depends(dependencies.require_admin),
) -> PublicationListResponse:
    result = publication_service.list_publications_admin(
        page=page,
        page_size=page_size,
        search=search,
        verification_status=verification_status,
        publication_type=publication_type,
        publication_year=publication_year,
        academic_year_id=academic_year_id,
        source=source,
        indexing=indexing,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PublicationListResponse(
        items=[PublicationResponse.model_validate(p) for p in result["items"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    )


@router.post(
    "/{publication_id}/verification", response_model=PublicationVerificationResponse
)
async def verify_publication(
    publication_id: str,
    request: VerificationRequest,
    admin: dict = Depends(dependencies.require_admin),
) -> PublicationVerificationResponse:
    publication, record = verification_service.verify_publication(
        publication_id=publication_id,
        admin_user=admin,
        action=request.action,
        reason=request.reason,
        notes=request.notes,
    )
    return PublicationVerificationResponse(
        publication=PublicationResponse.model_validate(publication),
        verification=verification_record_response(record),
    )


@router.get(
    "/{publication_id}/verification-history",
    response_model=list[VerificationRecordResponse],
)
async def verification_history(
    publication_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> list[VerificationRecordResponse]:
    records = verification_service.get_verification_history(publication_id)
    return [verification_record_response(r) for r in records]
