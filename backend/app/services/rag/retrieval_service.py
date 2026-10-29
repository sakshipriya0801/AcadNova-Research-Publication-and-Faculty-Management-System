"""Semantic retrieval over indexed document chunks.

Given a natural-language query, this service embeds the query, performs a
scoped vector similarity search and returns ranked, source-tagged chunks.  It
never generates an answer — that belongs to a later step.
"""

from typing import Optional

from app.config.settings import get_settings
from app.database import mongodb
from app.models.collections import DOCUMENTS, PUBLICATIONS
from app.services.rag import embedding_service, vector_store

_RESULT_FIELDS = (
    "document_id",
    "publication_id",
    "chunk_index",
    "page_start",
    "page_end",
    "relevance_score",
    "text",
)


def _active_document_ids(document_ids: list[str]) -> set[str]:
    """Documents that still exist, are not deleted, and have a live publication."""
    if not document_ids:
        return set()
    documents = list(
        mongodb.get_collection(DOCUMENTS).find(
            {"document_id": {"$in": document_ids}, "status": {"$ne": "deleted"}},
            {"document_id": 1, "publication_id": 1},
        )
    )
    if not documents:
        return set()
    publication_ids = {
        doc["publication_id"] for doc in documents if doc.get("publication_id")
    }
    active_publications: set[str] = set()
    if publication_ids:
        active_publications = {
            record["publication_id"]
            for record in mongodb.get_collection(PUBLICATIONS).find(
                {"publication_id": {"$in": list(publication_ids)}},
                {"publication_id": 1},
            )
        }
    return {
        doc["document_id"]
        for doc in documents
        if not doc.get("publication_id") or doc["publication_id"] in active_publications
    }


def _to_result(record: dict) -> dict:
    return {field: record.get(field) for field in _RESULT_FIELDS}


def retrieve(
    query: str,
    faculty_id: Optional[str] = None,
    publication_id: Optional[str] = None,
    document_id: Optional[str] = None,
    top_k: Optional[int] = None,
) -> dict:
    """Retrieve the most relevant chunks for ``query``.

    ``faculty_id`` is applied as a hard ownership scope; callers must derive it
    from the authenticated session, never from request input.
    """
    settings = get_settings()
    query = (query or "").strip()
    if not query:
        raise ValueError("query must not be empty")

    requested = top_k if top_k is not None else settings.rag_top_k
    limit = max(1, min(int(requested), int(settings.rag_max_top_k)))

    provider = embedding_service.get_embedding_provider()
    query_vector = provider.embed_text(query)

    candidates = vector_store.similarity_search(
        query_vector,
        top_k=limit,
        faculty_id=faculty_id,
        publication_id=publication_id,
        document_id=document_id,
    )

    minimum = float(settings.rag_min_relevance_score or 0.0)
    if minimum > 0.0:
        candidates = [
            record
            for record in candidates
            if float(record.get("relevance_score") or 0.0) >= minimum
        ]

    active = _active_document_ids(
        list({record.get("document_id") for record in candidates if record.get("document_id")})
    )
    results = [
        _to_result(record)
        for record in candidates
        if record.get("document_id") in active
    ]

    return {
        "query": query,
        "top_k": limit,
        "count": len(results),
        "search_mode": vector_store.search_mode(),
        "embedding_model": provider.model_name,
        "results": results,
    }
