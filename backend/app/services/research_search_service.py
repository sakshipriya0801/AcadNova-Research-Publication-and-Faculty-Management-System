"""Unified research-publication search orchestration (faculty + admin).

Reuses the existing external clients, publication persistence and faculty
lookups.  Internal searches are scoped by the authenticated session (faculty
see only their own records; administrators see all).  External searches are
public metadata lookups and never fabricate results.
"""

import re
from typing import Optional

from fastapi import HTTPException, status

from app.database import mongodb
from app.integrations.base import IntegrationError
from app.integrations.orcid import OrcidClient
from app.models.collections import PUBLICATIONS
from app.services import (
    external_publication_service,
    faculty_service,
    publication_service,
    scopus_service,
)
from app.utils.author_matching import normalize_orcid

SUPPORTED_EXTERNAL_SOURCES = ("crossref", "pubmed", "scopus", "web_of_science", "orcid")


def _collection():
    return mongodb.get_collection(PUBLICATIONS)


def _as_dict(result) -> dict:
    if isinstance(result, dict):
        return result
    return result.model_dump() if hasattr(result, "model_dump") else {}


def _external_result(result) -> dict:
    item = _as_dict(result)
    authors = [
        author.get("name") for author in (item.get("authors") or [])
        if isinstance(author, dict) and author.get("name")
    ]
    return {
        "kind": "external",
        "source": item.get("source"),
        "source_record_id": item.get("source_record_id"),
        "publication_id": None,
        "title": item.get("title"),
        "authors": authors,
        "publication_date": item.get("publication_date"),
        "publication_year": item.get("publication_year"),
        "doi": item.get("doi"),
        "journal": item.get("journal"),
        "indexing": item.get("indexing") or [],
        "external_identifiers": item.get("external_identifiers") or {},
        "verification_status": None,
        "faculty_id": None,
        "faculty_name": None,
        "importable": True,
    }


def _internal_result(publication: dict, faculty_name: Optional[str] = None) -> dict:
    publication_date = publication.get("publication_date")
    if hasattr(publication_date, "isoformat"):
        publication_date = publication_date.isoformat()
    return {
        "kind": "internal",
        "source": publication.get("source"),
        "source_record_id": publication.get("source_record_id"),
        "publication_id": publication.get("publication_id"),
        "title": publication.get("title"),
        "authors": publication.get("authors") or [],
        "publication_date": publication_date,
        "publication_year": publication.get("publication_year"),
        "doi": publication.get("doi"),
        "journal": publication.get("journal_name"),
        "indexing": publication.get("indexing") or [],
        "external_identifiers": publication.get("external_identifiers") or {},
        "verification_status": publication.get("verification_status"),
        "faculty_id": publication.get("faculty_id"),
        "faculty_name": faculty_name,
        "importable": False,
    }


def _faculty_name(faculty_id: str) -> Optional[str]:
    faculty = faculty_service.find_faculty_by_id(faculty_id)
    return faculty.get("name") if faculty else None


def _resolve_faculty(user: dict, q: str) -> dict:
    if user.get("role") == "admin":
        if not q:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Enter a Faculty ID or Employee ID.",
            )
        faculty = faculty_service.find_faculty_by_id(q) or (
            faculty_service.find_faculty_by_employee_id(q)
        )
        if faculty is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty not found")
        return faculty

    faculty = faculty_service.get_faculty_profile(user.get("faculty_id"))
    if faculty is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty profile not found")
    return faculty


def _scopus_author_search(q: str, page: int, page_size: int) -> dict:
    if not q:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter a Scopus Author ID.")
    return scopus_service.search_scopus(
        query="", author_id=q, page=page, page_size=page_size
    )


def _orcid_search(q: str, page: int, page_size: int) -> dict:
    orcid = normalize_orcid(q)
    if not orcid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Enter a valid ORCID identifier (e.g. 0000-0002-1825-0097).",
        )
    try:
        return OrcidClient().get_works(orcid, page=page, page_size=page_size)
    except IntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def _internal_field_search(user: dict, field: str, q: str, page: int, page_size: int) -> dict:
    query: dict = {}
    if user.get("role") != "admin":
        query["faculty_id"] = user.get("faculty_id")
    regex = {"$regex": re.escape(q), "$options": "i"}
    if field == "author":
        query["authors"] = regex
    elif field == "doi":
        query["doi"] = regex
    else:  # title
        query["title"] = regex

    collection = _collection()
    total = collection.count_documents(query)
    skip = (page - 1) * page_size
    items = list(collection.find(query).skip(skip).limit(page_size))
    return {"items": items, "total": total}


def search_research(
    user: dict,
    search_type: str,
    q: str,
    source: Optional[str],
    page: int,
    page_size: int,
) -> dict:
    q = (q or "").strip()

    # Identifier-based internal search.
    if search_type == "faculty":
        faculty = _resolve_faculty(user, q)
        result = publication_service.list_publications(
            faculty["faculty_id"], page=page, page_size=page_size, sort_order="desc"
        )
        items = [_internal_result(p, faculty.get("name")) for p in result["items"]]
        return _response(search_type, q, page, page_size, result["total"], items)

    if search_type == "scopus_author":
        data = _scopus_author_search(q, page, page_size)
        return _response(search_type, q, page, page_size, data["total"],
                         [_external_result(r) for r in data["results"]])

    if search_type == "orcid":
        data = _orcid_search(q, page, page_size)
        return _response(search_type, q, page, page_size, data["total"],
                         [_external_result(r) for r in data["results"]])

    # Internal + optional external for author name / DOI / title.
    field = {"author_name": "author", "doi": "doi", "title": "title"}[search_type]
    if not q:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter a search term.")

    internal = _internal_field_search(user, field, q, page, page_size)
    results = []
    for publication in internal["items"]:
        name = _faculty_name(publication.get("faculty_id")) if user.get("role") == "admin" else None
        results.append(_internal_result(publication, name))

    external_total = 0
    if source:
        ext = external_publication_service.search_external(
            source=source,
            query=q,
            page=page,
            page_size=page_size,
            author=q if search_type == "author_name" else None,
            title=q if search_type == "title" else None,
            doi=q if search_type == "doi" else None,
        )
        results.extend(_external_result(r) for r in ext["results"])
        external_total = ext["total"]

    return _response(search_type, q, page, page_size,
                     internal["total"] + external_total, results)


def _response(search_type, q, page, page_size, total, results) -> dict:
    return {
        "type": search_type,
        "query": q,
        "page": page,
        "page_size": page_size,
        "total": total,
        "results": results,
    }
