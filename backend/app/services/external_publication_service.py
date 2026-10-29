"""External source search and import orchestration.

Selects the requested integration client, executes the search, and normalizes
results.  Searching never persists anything to MongoDB.
"""

from typing import Optional

from fastapi import HTTPException, status

from app.integrations.base import IntegrationError
from app.integrations.crossref import CrossrefClient
from app.integrations.pubmed import PubMedClient
from app.integrations.scopus import ScopusClient
from app.integrations.web_of_science import WebOfScienceClient
from app.schemas.external_publication import ExternalPublicationResult
from app.services import (
    audit_service,
    author_matching_service,
    faculty_service,
    publication_service,
    user_service,
)

CLIENTS = {
    "crossref": CrossrefClient,
    "pubmed": PubMedClient,
    "scopus": ScopusClient,
    "web_of_science": WebOfScienceClient,
}


def _client(source: str):
    client_class = CLIENTS.get(source)
    if client_class is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source '{source}'",
        )
    return client_class()


def search_external(
    source: str,
    query: str = "",
    page: int = 1,
    page_size: int = 10,
    author: Optional[str] = None,
    title: Optional[str] = None,
    doi: Optional[str] = None,
) -> dict:
    client = _client(source)
    try:
        result = client.search(
            query=query,
            page=page,
            page_size=page_size,
            author=author,
            title=title,
            doi=doi,
        )
    except IntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return {
        "source": source,
        "page": page,
        "page_size": page_size,
        "total": result["total"],
        "results": result["results"],
    }


def get_external_record(source: str, record_id: str) -> ExternalPublicationResult:
    client = _client(source)
    try:
        record = client.get_by_identifier(record_id)
    except IntegrationError as exc:
        if exc.status_code == 502 and "HTTP 404" in exc.message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External record not found",
            )
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="External record not found"
        )
    return record


def import_external_publication(faculty_id: str, data: dict) -> dict:
    """Import an external publication for a faculty member.

    For ``source = "orcid"``, ``"scopus"`` or ``"web_of_science"`` the work
    authors are compared against the faculty record; unless the match is
    strong the caller must explicitly confirm authorship via
    ``author_match_confirmed``.  The matching evidence and the confirmation
    are recorded in the audit trail.
    """
    match = None
    requires_match = data.get("source") in ("orcid", "scopus", "web_of_science")

    if requires_match:
        faculty = faculty_service.get_faculty_profile(faculty_id)
        if faculty is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found"
            )
        match = author_matching_service.match_work_authors(
            faculty, data.get("authors") or []
        )
        if match["confidence"] != "high" and not data.get("author_match_confirmed"):
            factors = ", ".join(match["matching_factors"]) or "none"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Author match not confident (factors: {factors}); "
                    "set author_match_confirmed=true to confirm authorship"
                ),
            )

    publication = publication_service.create_imported_publication(faculty_id, data)

    if requires_match:
        user = user_service.find_user_by_faculty_id(faculty_id)
        audit_service.log_audit(
            user.get("user_id") if user else None,
            "publication.import",
            "publication",
            publication["publication_id"],
            new_value={
                "source": data.get("source"),
                "source_record_id": data.get("source_record_id"),
                "author_match_result": match["result"] if match else None,
                "author_match_confidence": match["confidence"] if match else None,
                "matching_factors": match["matching_factors"] if match else [],
                "author_match_confirmed": bool(data.get("author_match_confirmed")),
            },
        )

    return publication
