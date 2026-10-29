"""Scopus integration routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.routes import dependencies
from app.schemas.external_publication import ExternalPublicationResult, ExternalSearchResponse
from app.schemas.scopus import ScopusAuthorResponse
from app.services import scopus_service

router = APIRouter(prefix="/api/scopus", tags=["scopus"])


@router.get("/search", response_model=ExternalSearchResponse)
async def scopus_search(
    query: str = "",
    title: Optional[str] = None,
    author: Optional[str] = None,
    doi: Optional[str] = None,
    author_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalSearchResponse:
    if not any([query.strip(), title, author, doi, author_id]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "query must not be empty")
    result = scopus_service.search_scopus(
        query=query,
        page=page,
        page_size=page_size,
        author=author,
        title=title,
        doi=doi,
        author_id=author_id,
    )
    return ExternalSearchResponse(
        source="scopus",
        page=page,
        page_size=page_size,
        total=result["total"],
        results=result["results"],
    )


@router.get("/publication/{record_id}", response_model=ExternalPublicationResult)
async def scopus_publication(
    record_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExternalPublicationResult:
    return scopus_service.get_publication(record_id)


@router.get("/author/{author_id}", response_model=ScopusAuthorResponse)
async def scopus_author(
    author_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ScopusAuthorResponse:
    return scopus_service.get_author(author_id)
