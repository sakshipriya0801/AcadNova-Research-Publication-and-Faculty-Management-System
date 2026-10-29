"""Publication business/database logic (``publications`` collection)."""

import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database import mongodb
from app.models.collections import PUBLICATIONS
from app.models.enums import PublicationSource, VerificationStatus
from app.services import academic_year_service

# Fields a faculty member may update on their own publication.
ALLOWED_UPDATE_FIELDS = {
    "title",
    "authors",
    "publication_type",
    "faculty_author_position",
    "is_corresponding_author",
    "journal_name",
    "conference_name",
    "publisher",
    "doi",
    "issn",
    "isbn",
    "volume",
    "issue",
    "pages",
    "publication_date",
    "abstract",
    "keywords",
    "indexing",
    "collaboration_type",
    "external_institution",
    "source_url",
    "pdf_url",
    "sub_type",
}

# Whitelist of allowed sort fields (never pass user input straight to Mongo).
SORT_FIELDS = {
    "publication_date": "publication_date",
    "created_at": "created_at",
    "title": "title",
}

DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi.org/",
    "doi:",
)


def _collection():
    return mongodb.get_collection(PUBLICATIONS)


def _enum_value(value):
    """Return the string value of an enum, otherwise the value unchanged."""
    return value.value if isinstance(value, Enum) else value


def _to_datetime(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _clean_strings(values) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values or []:
        if isinstance(item, str):
            value = item.strip()
            if value and value not in seen:
                cleaned.append(value)
                seen.add(value)
    return cleaned


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Normalize a DOI to a canonical lowercase form (or None if empty)."""
    if doi is None:
        return None
    doi = doi.strip()
    if not doi:
        return None
    doi = doi.lower()
    for prefix in DOI_PREFIXES:
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi or None


def find_duplicate_doi(
    doi: Optional[str], exclude_publication_id: Optional[str] = None
) -> Optional[dict]:
    """Return an existing publication with the same normalized DOI."""
    normalized = normalize_doi(doi)
    if normalized is None:
        return None
    query: dict = {"doi": normalized}
    if exclude_publication_id:
        query["publication_id"] = {"$ne": exclude_publication_id}
    return _collection().find_one(query)


def _ensure_unique_doi(
    doi: Optional[str], exclude_publication_id: Optional[str] = None
) -> None:
    if find_duplicate_doi(doi, exclude_publication_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This publication already exists in the system.",
        )


def create_publication(faculty_id: str, data: dict) -> dict:
    """Validate and insert a manual publication for the given faculty."""
    publication_date = data.get("publication_date")
    academic_year = academic_year_service.resolve_academic_year(publication_date)

    authors = _clean_strings(data.get("authors"))
    if not authors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="authors must not be empty",
        )

    author_count = len(authors)
    faculty_author_position = data.get("faculty_author_position")
    if faculty_author_position is not None and (
        faculty_author_position < 1 or faculty_author_position > author_count
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="faculty_author_position must be between 1 and the number of authors",
        )

    doi = normalize_doi(data.get("doi"))
    _ensure_unique_doi(doi)

    now = datetime.now(timezone.utc)
    publication = {
        "publication_id": str(uuid4()),
        "title": data.get("title"),
        "authors": authors,
        "author_count": author_count,
        "faculty_id": faculty_id,
        "faculty_author_position": faculty_author_position,
        "is_corresponding_author": bool(data.get("is_corresponding_author", False)),
        "publication_type": _enum_value(data.get("publication_type")),
        "journal_name": data.get("journal_name"),
        "conference_name": data.get("conference_name"),
        "publisher": data.get("publisher"),
        "doi": doi,
        "issn": data.get("issn"),
        "isbn": data.get("isbn"),
        "volume": data.get("volume"),
        "issue": data.get("issue"),
        "pages": data.get("pages"),
        "publication_date": _to_datetime(publication_date),
        "publication_year": publication_date.year,
        "abstract": data.get("abstract"),
        "keywords": _clean_strings(data.get("keywords")),
        "source": PublicationSource.MANUAL.value,
        "source_record_id": None,
        "source_url": data.get("source_url"),
        "pdf_url": data.get("pdf_url"),
        "indexing": _clean_strings(data.get("indexing")),
        "collaboration_type": data.get("collaboration_type"),
        "external_institution": data.get("external_institution"),
        "sub_type": data.get("sub_type"),
        "verification_status": VerificationStatus.PENDING.value,
        "points_awarded": 0,
        "academic_year_id": academic_year["academic_year_id"],
        "created_at": now,
        "updated_at": now,
    }
    _collection().insert_one(publication)
    return publication


_MONTH_ABBREV = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_partial_date(value) -> Optional[date]:
    """Parse a date from common external-source string formats."""
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass

    match = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return date(year, month, 1)

    if s.isdigit() and len(s) == 4:
        return date(int(s), 7, 1)

    match = re.match(r"^(\d{4})\s+([A-Za-z]{3})(?:\s+(\d{1,2}))?", s)
    if match:
        year = int(match.group(1))
        month = _MONTH_ABBREV.get(match.group(2).lower())
        if month:
            day = int(match.group(3)) if match.group(3) else 1
            return date(year, month, day)
    return None


def _resolve_import_date(data: dict) -> date:
    parsed = _parse_partial_date(data.get("publication_date"))
    if parsed is not None:
        return parsed
    year = data.get("publication_year")
    if year:
        return date(int(year), 7, 1)
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        "publication_date or publication_year is required",
    )


def find_duplicate_source_record(
    source: str, source_record_id: Optional[str]
) -> Optional[dict]:
    if not source or not source_record_id:
        return None
    return _collection().find_one(
        {"source": source, "source_record_id": source_record_id}
    )


def _resolve_import_academic_year(data: dict, publication_date: date) -> dict:
    """Resolve the academic year an imported publication is claimed for.

    An explicitly selected ``academic_year_id`` (validated to exist) wins;
    otherwise the academic year is derived from the publication date using the
    institution's 1 July → 30 June mapping.  Never creates a year implicitly.
    """
    year_id = data.get("academic_year_id")
    if year_id:
        academic_year = academic_year_service.get_academic_year(year_id)
        if academic_year is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Selected academic year was not found",
            )
        return academic_year

    return academic_year_service.resolve_academic_year(publication_date)


def create_imported_publication(faculty_id: str, data: dict) -> dict:
    """Create a publication from an external source (never auto-verifies)."""
    source = data.get("source")
    source_record_id = data.get("source_record_id")

    author_names = [
        author.get("name")
        for author in (data.get("authors") or [])
        if isinstance(author, dict) and author.get("name")
    ]
    authors = _clean_strings(author_names)
    if not authors:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="authors must not be empty"
        )

    publication_date = _resolve_import_date(data)
    academic_year = _resolve_import_academic_year(data, publication_date)

    doi = normalize_doi(data.get("doi"))
    _ensure_unique_doi(doi)

    if find_duplicate_source_record(source, source_record_id) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This publication has already been imported",
        )

    now = datetime.now(timezone.utc)
    publication = {
        "publication_id": str(uuid4()),
        "title": data.get("title"),
        "authors": authors,
        "author_count": len(authors),
        "faculty_id": faculty_id,
        "faculty_author_position": None,
        "is_corresponding_author": False,
        "publication_type": "research_publication",
        "journal_name": data.get("journal"),
        "conference_name": data.get("conference"),
        "publisher": data.get("publisher"),
        "doi": doi,
        "issn": None,
        "isbn": None,
        "volume": None,
        "issue": None,
        "pages": None,
        "publication_date": _to_datetime(publication_date),
        "publication_year": publication_date.year,
        "abstract": data.get("abstract"),
        "keywords": [],
        "source": source,
        "source_record_id": source_record_id,
        "source_url": data.get("url"),
        "pdf_url": None,
        "indexing": _clean_strings(data.get("indexing") or []),
        "collaboration_type": None,
        "external_institution": None,
        "sub_type": None,
        "verification_status": VerificationStatus.PENDING.value,
        "points_awarded": 0,
        "academic_year_id": academic_year["academic_year_id"],
        "created_at": now,
        "updated_at": now,
    }
    _collection().insert_one(publication)
    return publication


def get_publication_by_id(publication_id: str, faculty_id: str) -> dict:
    """Return a publication owned by the faculty, or raise 404."""
    publication = _collection().find_one({"publication_id": publication_id})
    if publication is None or publication.get("faculty_id") != faculty_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found"
        )
    return publication


def find_publication_by_id(publication_id: str) -> Optional[dict]:
    """Return a publication by id without ownership checks, or None."""
    return _collection().find_one({"publication_id": publication_id})


def list_publications(
    faculty_id: str,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    publication_type: Optional[str] = None,
    verification_status: Optional[str] = None,
    publication_year: Optional[int] = None,
    academic_year_id: Optional[str] = None,
    source: Optional[str] = None,
    indexing: Optional[str] = None,
    sort_by: str = "publication_date",
    sort_order: str = "desc",
) -> dict:
    """Return a page of publications owned by the faculty."""
    query: dict = {"faculty_id": faculty_id}

    if search:
        regex = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [
            {"title": regex},
            {"journal_name": regex},
            {"conference_name": regex},
            {"doi": regex},
        ]
    if publication_type:
        query["publication_type"] = publication_type
    if verification_status:
        query["verification_status"] = verification_status
    if publication_year is not None:
        query["publication_year"] = publication_year
    if academic_year_id:
        query["academic_year_id"] = academic_year_id
    if source:
        query["source"] = source
    if indexing:
        query["indexing"] = {"$regex": f"^{re.escape(indexing)}$", "$options": "i"}

    total = _collection().count_documents(query)

    sort_field = SORT_FIELDS.get(sort_by, SORT_FIELDS["publication_date"])
    direction = DESCENDING if sort_order == "desc" else ASCENDING

    skip = (page - 1) * page_size
    cursor = (
        _collection()
        .find(query)
        .sort(sort_field, direction)
        .skip(skip)
        .limit(page_size)
    )
    items = list(cursor)

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


def update_publication(publication_id: str, faculty_id: str, data: dict) -> dict:
    """Update an owned publication, returning the updated document."""
    existing = get_publication_by_id(publication_id, faculty_id)

    updates = {k: v for k, v in data.items() if k in ALLOWED_UPDATE_FIELDS}

    if "authors" in updates:
        authors = _clean_strings(updates.get("authors"))
        if not authors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="authors must not be empty",
            )
        updates["authors"] = authors
        updates["author_count"] = len(authors)

    author_count = updates.get("author_count", existing.get("author_count"))
    if "faculty_author_position" in updates:
        position = updates["faculty_author_position"]
        if position is not None and (
            author_count is None or position < 1 or position > author_count
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="faculty_author_position must be between 1 and the number of authors",
            )

    if "doi" in updates:
        normalized = normalize_doi(updates["doi"])
        if normalized is not None and normalized != existing.get("doi"):
            _ensure_unique_doi(normalized, exclude_publication_id=publication_id)
        updates["doi"] = normalized

    if "publication_date" in updates:
        publication_date = updates["publication_date"]
        academic_year = academic_year_service.resolve_academic_year(publication_date)
        updates["publication_date"] = _to_datetime(publication_date)
        updates["publication_year"] = publication_date.year
        updates["academic_year_id"] = academic_year["academic_year_id"]

    if "publication_type" in updates:
        updates["publication_type"] = _enum_value(updates["publication_type"])

    if "keywords" in updates:
        updates["keywords"] = _clean_strings(updates["keywords"])
    if "indexing" in updates:
        updates["indexing"] = _clean_strings(updates["indexing"])

    for field in (
        "title",
        "journal_name",
        "conference_name",
        "publisher",
        "issn",
        "isbn",
        "volume",
        "issue",
        "pages",
        "collaboration_type",
        "external_institution",
        "source_url",
        "pdf_url",
        "sub_type",
    ):
        if field in updates and isinstance(updates[field], str):
            updates[field] = updates[field].strip() or None

    if not updates:
        return existing

    updates["updated_at"] = datetime.now(timezone.utc)
    return _collection().find_one_and_update(
        {"publication_id": publication_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )


def delete_publication(publication_id: str, faculty_id: str) -> None:
    """Delete an owned publication (raises 404 if missing/not owned)."""
    get_publication_by_id(publication_id, faculty_id)
    _collection().delete_one({"publication_id": publication_id})
    # Remove orphaned knowledge-base chunks so deleted publications are never
    # surfaced as AI evidence. Imported lazily to avoid a circular import.
    try:
        from app.services.rag import vector_store

        vector_store.delete_publication_chunks(publication_id)
    except Exception:  # pragma: no cover - cleanup must never block deletion
        pass


def list_publications_admin(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    verification_status: Optional[str] = None,
    publication_type: Optional[str] = None,
    publication_year: Optional[int] = None,
    academic_year_id: Optional[str] = None,
    source: Optional[str] = None,
    indexing: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """Return a page of all publications for admin review (no faculty filter)."""
    query: dict = {}
    if search:
        regex = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [
            {"title": regex},
            {"journal_name": regex},
            {"conference_name": regex},
            {"doi": regex},
        ]
    if publication_type:
        query["publication_type"] = publication_type
    if verification_status:
        query["verification_status"] = verification_status
    if publication_year is not None:
        query["publication_year"] = publication_year
    if academic_year_id:
        query["academic_year_id"] = academic_year_id
    if source:
        query["source"] = source
    if indexing:
        query["indexing"] = {"$regex": f"^{re.escape(indexing)}$", "$options": "i"}

    total = _collection().count_documents(query)

    sort_field = SORT_FIELDS.get(sort_by, SORT_FIELDS["created_at"])
    direction = DESCENDING if sort_order == "desc" else ASCENDING

    skip = (page - 1) * page_size
    cursor = (
        _collection()
        .find(query)
        .sort(sort_field, direction)
        .skip(skip)
        .limit(page_size)
    )
    items = list(cursor)

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }
