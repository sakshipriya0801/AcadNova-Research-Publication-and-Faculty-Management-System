"""Unified research publication search route (faculty + admin)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routes import dependencies
from app.schemas.research_search import (
    ResearchSearchResponse,
    ResearchSearchResult,
)
from app.services import research_search_service

router = APIRouter(prefix="/api/search", tags=["search"])

_SEARCH_TYPES = (
    "faculty",
    "scopus_author",
    "orcid",
    "author_name",
    "doi",
    "title",
)


@router.get("/research", response_model=ResearchSearchResponse)
async def research_search(
    type: str = Query(..., description="One of: " + ", ".join(_SEARCH_TYPES)),
    q: str = "",
    source: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ResearchSearchResponse:
    if type not in _SEARCH_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported search type '{type}'"
        )
    result = research_search_service.search_research(
        user=user,
        search_type=type,
        q=q,
        source=source,
        page=page,
        page_size=page_size,
    )
    return ResearchSearchResponse(
        type=result["type"],
        query=result["query"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        results=[ResearchSearchResult(**item) for item in result["results"]],
    )
