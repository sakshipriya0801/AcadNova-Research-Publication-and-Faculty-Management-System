"""Web of Science integration routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routes import dependencies
from app.schemas.external_publication import ExternalPublicationResult, ExternalSearchResponse
from app.services import web_of_science_service

router = APIRouter(prefix="/api/web-of-science", tags=["web-of-science"])


@router.get("/search", response_model=ExternalSearchResponse)
async def wos_search(
    query: str = "",
    title: Optional[str] = None,
    author: Optional[str] = None,
    doi: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalSearchResponse:
    if not any([query.strip(), title, author, doi]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "query must not be empty")
    result = web_of_science_service.search_web_of_science(
        query=query, page=page, page_size=page_size, author=author, title=title, doi=doi
    )
    return ExternalSearchResponse(
        source="web_of_science",
        page=page,
        page_size=page_size,
        total=result["total"],
        results=result["results"],
    )


@router.get("/publication/{record_id}", response_model=ExternalPublicationResult)
async def wos_publication(
    record_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalPublicationResult:
    return web_of_science_service.get_publication(record_id)


@router.get("/researcher/{researcher_id}")
async def wos_researcher(
    researcher_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
):
    return web_of_science_service.get_researcher(researcher_id)
