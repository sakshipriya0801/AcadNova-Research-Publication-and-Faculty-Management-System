"""Vector storage abstraction backed by MongoDB.

Embeddings are stored alongside chunk metadata in the ``document_chunks``
collection.  Similarity search prefers a MongoDB Atlas ``$vectorSearch`` index
when one is available; otherwise it falls back to an in-process brute-force
cosine scan over the stored vectors.

The two modes are reported explicitly via :func:`search_mode` so that a
brute-force scan is never presented as an approximated Atlas vector index.
Keyword/text search is intentionally not used as a substitute for semantic
search.
"""

from datetime import datetime, timezone
from typing import Optional

from app.database import mongodb
from app.models.collections import DOCUMENT_CHUNKS

_ATLAS_VECTOR_INDEX_NAME = "document_chunks_vector_index"
_MAX_CANDIDATES = 10000
_vector_index_cache: Optional[bool] = None


def _collection():
    return mongodb.get_collection(DOCUMENT_CHUNKS)


def _scope_filter(
    faculty_id: Optional[str],
    publication_id: Optional[str],
    document_id: Optional[str],
) -> dict:
    query: dict = {}
    if faculty_id:
        query["faculty_id"] = faculty_id
    if publication_id:
        query["publication_id"] = publication_id
    if document_id:
        query["document_id"] = document_id
    return query


def _atlas_vector_search_available() -> bool:
    """Probe once whether the deployment supports ``$vectorSearch``."""
    global _vector_index_cache
    if _vector_index_cache is not None:
        return _vector_index_cache
    try:
        list(
            _collection().aggregate(
                [
                    {
                        "$vectorSearch": {
                            "index": _ATLAS_VECTOR_INDEX_NAME,
                            "path": "embedding",
                            "queryVector": [0.0],
                            "numCandidates": 1,
                            "limit": 1,
                        }
                    }
                ]
            )
        )
        _vector_index_cache = True
    except Exception:
        _vector_index_cache = False
    return _vector_index_cache


def search_mode() -> str:
    """Return the active search strategy (never claims an index it lacks)."""
    return "vector_index" if _atlas_vector_search_available() else "vector_brute_force"


def upsert_document_chunks(document_id: str, chunks: list[dict]) -> int:
    """Replace all stored chunks for a document (idempotent by construction)."""
    collection = _collection()
    collection.delete_many({"document_id": document_id})
    if not chunks:
        return 0
    now = datetime.now(timezone.utc)
    documents = []
    for chunk in chunks:
        record = dict(chunk)
        record.setdefault("created_at", now)
        record["updated_at"] = now
        documents.append(record)
    collection.insert_many(documents)
    return len(documents)


def delete_document(document_id: str) -> int:
    """Delete every stored chunk/vector for a document."""
    result = _collection().delete_many({"document_id": document_id})
    return result.deleted_count


def delete_publication_chunks(publication_id: str) -> int:
    """Delete every stored chunk/vector for a publication (orphan cleanup)."""
    result = _collection().delete_many({"publication_id": publication_id})
    return result.deleted_count


def count_for_document(document_id: str) -> int:
    return _collection().count_documents({"document_id": document_id})


def list_document_chunks(document_id: str) -> list[dict]:
    """Return a document's chunks ordered by index, without embeddings."""
    cursor = _collection().find(
        {"document_id": document_id},
        {
            "_id": 0,
            "embedding": 0,
            "chunk_id": 0,
            "processing_version": 0,
        },
    ).sort("chunk_index", 1)
    return list(cursor)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(length):
        av = a[i]
        bv = b[i]
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))


def similarity_search(
    query_vector: list[float],
    top_k: int,
    faculty_id: Optional[str] = None,
    publication_id: Optional[str] = None,
    document_id: Optional[str] = None,
) -> list[dict]:
    """Return the ``top_k`` most similar chunks, ordered by relevance."""
    if not query_vector or top_k <= 0:
        return []

    query = _scope_filter(faculty_id, publication_id, document_id)

    if _atlas_vector_search_available():
        pipeline = [
            {
                "$vectorSearch": {
                    "index": _ATLAS_VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": max(top_k * 10, 100),
                    "limit": top_k,
                    **({"filter": query} if query else {}),
                }
            },
            {"$project": {"embedding": 0}},
        ]
        results = []
        for record in _collection().aggregate(pipeline):
            record["relevance_score"] = record.pop("vectorSearchScore", 0.0)
            results.append(record)
        return results

    collection = _collection()
    cursor = collection.find(query).limit(_MAX_CANDIDATES)
    scored: list[tuple[float, dict]] = []
    for record in cursor:
        embedding = record.get("embedding")
        if not embedding:
            continue
        score = _cosine_similarity(query_vector, embedding)
        record.pop("embedding", None)
        record["relevance_score"] = score
        scored.append((score, record))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in scored[:top_k]]
