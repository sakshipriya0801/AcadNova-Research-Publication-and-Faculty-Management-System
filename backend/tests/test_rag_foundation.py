"""RAG foundation tests (Step 15A).

Covers extraction reuse, cleaning, deterministic chunking, embedding
abstraction, chunk storage, idempotent reprocessing, retrieval ranking,
ownership isolation and safe failure handling.  No external AI provider is
required — the deterministic ``test`` embedding provider is used throughout.
"""

import uuid

import pymupdf
import pytest

from app.config.settings import get_settings
from app.database import mongodb
from app.models.collections import (
    ACADEMIC_YEARS,
    DOCUMENT_CHUNKS,
    DOCUMENT_CONTENTS,
    FACULTY,
    PUBLICATIONS,
    USERS,
)
from app.services import document_service
from app.services.rag import (
    chunker,
    document_processor,
    embedding_service,
    text_cleaner,
    vector_store,
)
from app.utils import security

PASSWORD = "StrongPassword123"


@pytest.fixture(autouse=True)
def _rag_settings(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _ensure_year():
    db = mongodb.get_database()
    if db[ACADEMIC_YEARS].find_one({"name": "2025-2026"}) is None:
        db[ACADEMIC_YEARS].insert_one(
            {
                "academic_year_id": str(uuid.uuid4()),
                "name": "2025-2026",
                "start_date": "2025-07-01",
                "end_date": "2026-06-30",
                "is_current": True,
            }
        )


def _admin_token(client) -> str:
    email = f"ragadmin_{uuid.uuid4().hex[:10]}@example.com"
    mongodb.get_collection(USERS).insert_one(
        {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password_hash": security.hash_password(PASSWORD),
            "role": "admin",
            "faculty_id": None,
            "is_active": True,
        }
    )
    return client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]


def _register_faculty(client) -> dict:
    email = f"ragf_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "RAG Faculty",
            "employee_id": "RAG_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"email": email, "token": token, "faculty_id": reg.json()["faculty_id"]}


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_publication(client, token, title="RAG Publication") -> dict:
    _ensure_year()
    resp = client.post(
        "/api/publications",
        headers=_h(token),
        json={
            "title": title,
            "authors": ["RAG Faculty"],
            "publication_type": "research_publication",
            "faculty_author_position": 1,
            "publication_date": "2025-08-15",
            "indexing": ["Scopus"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_pdf(page_texts: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def _upload(client, token, pid, data: bytes) -> str:
    resp = client.post(
        f"/api/publications/{pid}/documents",
        headers=_h(token),
        data={"document_type": "research_paper"},
        files={"file": ("rag.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _processed_doc(client, token, pid, page_texts) -> str:
    doc_id = _upload(client, token, pid, _make_pdf(page_texts))
    resp = client.post(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/process",
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return doc_id


# --- 2. Text cleaning --------------------------------------------------------

def test_text_cleaner_normalises_without_destroying_content():
    raw = "Title:\t  Study of  Materials \x0c\n\n\n\n2.   Methods\n  We use\nX^n + y.\n"
    cleaned = text_cleaner.clean_text(raw)
    assert "\t" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "2. Methods" in cleaned
    assert "X^n + y." in cleaned  # punctuation/math preserved


def test_clean_pages_drops_empty_pages_but_keeps_numbers():
    pages = [
        {"page_number": 1, "text": "   "},
        {"page_number": 2, "text": "Real content here."},
    ]
    cleaned = text_cleaner.clean_pages(pages)
    assert len(cleaned) == 1
    assert cleaned[0]["page_number"] == 2


# --- 3-4. Deterministic chunking + page metadata -----------------------------

def test_chunking_is_deterministic_and_page_aware():
    pages = [
        {"page_number": 1, "text": " ".join(f"a{i}" for i in range(12))},
        {"page_number": 2, "text": " ".join(f"b{i}" for i in range(12))},
    ]
    first = chunker.chunk_pages(pages, chunk_size=10, overlap=4)
    second = chunker.chunk_pages(pages, chunk_size=10, overlap=4)
    assert first == second
    assert [c.chunk_index for c in first] == list(range(len(first)))
    assert all(c.page_start is not None and c.page_end is not None for c in first)
    assert first[0].page_start == 1
    assert any(c.page_end == 2 for c in first)


def test_chunking_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        chunker.chunk_pages([{"page_number": 1, "text": "x"}], chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        chunker.chunk_pages([{"page_number": 1, "text": "x"}], chunk_size=5, overlap=5)


# --- 6. Mock/deterministic embedding provider --------------------------------

def test_test_embedding_provider_is_deterministic():
    provider = embedding_service.TestEmbeddingProvider(dimensions=32)
    a = provider.embed_text("semantic retrieval system")
    b = provider.embed_text("semantic retrieval system")
    assert a == b and len(a) == 32
    assert provider.embed_text("completely different words") != a


# --- 1. PDF text extraction (reused Step 13 pipeline) ------------------------

def test_pdf_extraction_is_reused(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    doc_id = _upload(client, info["token"], pub["publication_id"], _make_pdf(["Extracted body text."]))
    resp = client.post(
        f"/api/publications/{pub['publication_id']}/documents/{doc_id}/process",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    content = mongodb.get_collection(DOCUMENT_CONTENTS).find_one({"document_id": doc_id})
    assert content and content["text_length"] > 0
    assert content["pages"][0]["page_number"] == 1


# --- 7. Chunk storage + 14. status endpoint ----------------------------------

def test_processing_stores_chunks_and_reports_status(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _upload(client, info["token"], pid, _make_pdf(["Some research content about materials."]))

    before = client.get(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/status", headers=_h(info["token"])
    )
    assert before.status_code == 200
    assert before.json()["rag_status"] == "pending"

    done = client.post(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/process", headers=_h(info["token"])
    )
    body = done.json()
    assert body["rag_status"] == "completed"
    assert body["chunk_count"] >= 1 and body["embedding_count"] == body["chunk_count"]
    assert body["processing_version"] == document_processor.PROCESSING_VERSION

    stored = list(
        mongodb.get_collection(DOCUMENT_CHUNKS).find({"document_id": doc_id})
    )
    assert len(stored) == body["chunk_count"]
    assert stored[0]["embedding"] and stored[0]["faculty_id"] == info["faculty_id"]
    assert stored[0]["publication_id"] == pid


# --- 8. Idempotent reprocessing ----------------------------------------------

def test_reprocessing_does_not_duplicate_chunks(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _processed_doc(
        client, info["token"], pid, ["Repeatable content about testing pipelines."]
    )
    first = list(mongodb.get_collection(DOCUMENT_CHUNKS).find({"document_id": doc_id}))
    resp = client.post(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/process", headers=_h(info["token"])
    )
    second = list(mongodb.get_collection(DOCUMENT_CHUNKS).find({"document_id": doc_id}))
    assert resp.json()["chunk_count"] == len(first) == len(second)
    assert [c["text"] for c in first] == [c["text"] for c in second]


# --- 9. Retrieval ranking ----------------------------------------------------

def test_retrieval_ranks_relevant_chunks_first(client, monkeypatch):
    monkeypatch.setenv("RAG_CHUNK_SIZE", "20")
    monkeypatch.setenv("RAG_CHUNK_OVERLAP", "0")
    get_settings.cache_clear()
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    quantum = " ".join(["quantum"] * 40)
    custard = " ".join(["custard"] * 40)
    _processed_doc(client, info["token"], pid, [quantum, custard])

    resp = client.post(
        "/api/rag/retrieve",
        headers=_h(info["token"]),
        json={"query": "quantum", "publication_id": pid, "top_k": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["retrieved_chunks"] >= 1
    assert body["results"][0]["page_start"] == 1
    assert "quantum" in body["results"][0]["text"]
    assert body["search_mode"] == "vector_brute_force"


# --- 15. Chunks endpoint never exposes embeddings/paths ----------------------

def test_chunks_endpoint_hides_embeddings_and_paths(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _processed_doc(client, info["token"], pid, ["Chunk visibility content."])
    resp = client.get(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/chunks", headers=_h(info["token"])
    )
    assert resp.status_code == 200
    payload = resp.content.decode()
    assert "embedding" not in payload
    assert "storage_path" not in payload
    assert "chunk_id" not in payload
    assert resp.json()["chunk_count"] >= 1


# --- 10-11. Ownership isolation ----------------------------------------------

def test_document_ownership_enforced(client):
    _ensure_year()
    a = _register_faculty(client)
    b = _register_faculty(client)
    pub = _create_publication(client, a["token"])
    doc_id = _processed_doc(client, a["token"], pub["publication_id"], ["Private content."])
    resp = client.get(
        f"/api/publications/{pub['publication_id']}/documents/{doc_id}/knowledge/status",
        headers=_h(b["token"]),
    )
    assert resp.status_code == 403


def test_cross_faculty_retrieval_blocked(client):
    _ensure_year()
    a = _register_faculty(client)
    b = _register_faculty(client)
    pub_a = _create_publication(client, a["token"], title="A")
    pub_b = _create_publication(client, b["token"], title="B")
    doc_b = _processed_doc(client, b["token"], pub_b["publication_id"], ["secret custard recipe"])
    _processed_doc(client, a["token"], pub_a["publication_id"], ["public quantum notes"])

    resp = client.post(
        "/api/rag/retrieve", headers=_h(a["token"]), json={"query": "custard"}
    )
    assert resp.status_code == 200
    doc_ids = {item["document_id"] for item in resp.json()["results"]}
    assert doc_b not in doc_ids

    blocked = client.post(
        "/api/rag/retrieve",
        headers=_h(a["token"]),
        json={"query": "custard", "document_id": doc_b},
    )
    assert blocked.status_code == 403


# --- 12. Deleted documents excluded ------------------------------------------

def test_deleted_document_chunks_removed_and_excluded(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _processed_doc(client, info["token"], pid, ["deletable quantum content"])
    assert vector_store.count_for_document(doc_id) >= 1

    resp = client.delete(
        f"/api/publications/{pid}/documents/{doc_id}", headers=_h(info["token"])
    )
    assert resp.status_code == 204
    assert vector_store.count_for_document(doc_id) == 0

    retrieved = client.post(
        "/api/rag/retrieve", headers=_h(info["token"]), json={"query": "deletable quantum"}
    )
    assert retrieved.status_code == 200
    assert all(item["document_id"] != doc_id for item in retrieved.json()["results"])


# --- 5. Empty/scanned PDF ----------------------------------------------------

def test_scanned_pdf_without_text_fails_safely(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _upload(client, info["token"], pid, _make_pdf([""]))
    resp = client.post(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/process",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rag_status"] == "failed"
    assert body["rag_error"] == document_processor.EMPTY_TEXT_MESSAGE
    assert vector_store.count_for_document(doc_id) == 0


# --- 13. Processing failure + provider-not-configured ------------------------

def test_corrupt_pdf_processing_becomes_failed(client):
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _upload(client, info["token"], pid, b"%PDF-1.4 not a real pdf body")
    resp = client.post(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/process",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rag_status"] == "failed"
    assert body["rag_error"]
    # Never stuck in "processing".
    doc = document_service.get_document(doc_id)
    assert doc["rag_status"] == "failed"


def test_embedding_provider_not_configured_fails_safely(client, monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "")
    get_settings.cache_clear()
    _ensure_year()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]
    doc_id = _upload(client, info["token"], pid, _make_pdf(["content requiring embeddings"]))
    resp = client.post(
        f"/api/publications/{pid}/documents/{doc_id}/knowledge/process",
        headers=_h(info["token"]),
    )
    body = resp.json()
    assert body["rag_status"] == "failed"
    assert body["rag_error"] == "AI provider is not configured."

    retrieve = client.post(
        "/api/rag/retrieve", headers=_h(info["token"]), json={"query": "content"}
    )
    assert retrieve.status_code == 503
    assert retrieve.json()["detail"] == "AI provider is not configured."


# --- 11/validation: query + id bounds ----------------------------------------

def test_invalid_retrieve_requests_rejected(client):
    _ensure_year()
    info = _register_faculty(client)
    empty = client.post("/api/rag/retrieve", headers=_h(info["token"]), json={"query": ""})
    assert empty.status_code == 400
    too_long = client.post(
        "/api/rag/retrieve", headers=_h(info["token"]), json={"query": "x" * 5000}
    )
    assert too_long.status_code == 400
    bad_topk = client.post(
        "/api/rag/retrieve", headers=_h(info["token"]), json={"query": "ok", "top_k": 999}
    )
    assert bad_topk.status_code == 400
    unknown = client.post(
        "/api/rag/retrieve",
        headers=_h(info["token"]),
        json={"query": "ok", "document_id": "does-not-exist"},
    )
    assert unknown.status_code == 404


def test_retrieve_requires_authentication(client):
    resp = client.post("/api/rag/retrieve", json={"query": "anything"})
    assert resp.status_code == 401
