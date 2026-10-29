"""Step 15B — database & API integration tests.

These tests assert that API writes actually persist in MongoDB (and the
filesystem for documents) and that browser CORS works for the dev origin.
They run against the isolated test database created by the shared conftest.
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
    DOCUMENTS,
    FACULTY,
    FACULTY_POINTS,
    PUBLICATIONS,
    USERS,
    VERIFICATION_RECORDS,
)
from app.utils import security
from scripts.seed_rules import seed_eligibility_rules, seed_publication_rules

PASSWORD = "StrongPassword123"


@pytest.fixture(autouse=True)
def _rag_provider(monkeypatch):
    """Use the deterministic embedding provider; no external AI required."""
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _seed():
    seed_publication_rules()
    seed_eligibility_rules()
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
    email = f"intadmin_{uuid.uuid4().hex[:10]}@example.com"
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
    email = f"intf_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Integration Faculty",
            "employee_id": "INT_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    assert reg.status_code == 201, reg.text
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"email": email, "token": token, "faculty_id": reg.json()["faculty_id"]}


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_publication(client, token, title="Integration Publication") -> dict:
    resp = client.post(
        "/api/publications",
        headers=_h(token),
        json={
            "title": title,
            "authors": ["Integration Faculty", "Second Author"],
            "publication_type": "research_publication",
            "faculty_author_position": 1,
            "publication_date": "2025-08-15",
            "journal_name": "Journal of Integration",
            "doi": f"10.9999/int.{uuid.uuid4().hex[:8]}",
            "indexing": ["Scopus"],
            "is_corresponding_author": True,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_pdf(text="Integration test PDF body text.") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


# --- 1-2. Connection & health ------------------------------------------------

def test_health_reports_database_connected(client):
    db = mongodb.get_database()
    assert db.command("ping").get("ok") == 1.0
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "connected"}


# --- 3-5. Auth persistence ---------------------------------------------------

def test_register_persists_user_and_faculty(client):
    info = _register_faculty(client)
    user = mongodb.get_collection(USERS).find_one({"email": info["email"]})
    assert user is not None
    assert user.get("password_hash") not in (None, PASSWORD)
    assert user.get("faculty_id") == info["faculty_id"]
    faculty = mongodb.get_collection(FACULTY).find_one(
        {"faculty_id": info["faculty_id"]}
    )
    assert faculty is not None


def test_login_issues_jwt_accepted_by_me(client):
    info = _register_faculty(client)
    token = client.post(
        "/api/auth/login", json={"email": info["email"], "password": PASSWORD}
    ).json()["access_token"]
    resp = client.get("/api/auth/me", headers=_h(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == info["email"]
    assert body["faculty_id"] == info["faculty_id"]


# --- 6-7. Publication & faculty profile persistence --------------------------

def test_publication_create_update_persist(client):
    _seed()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    stored = mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": pub["publication_id"]}
    )
    assert stored is not None
    assert stored["faculty_id"] == info["faculty_id"]

    resp = client.put(
        f"/api/publications/{pub['publication_id']}",
        headers=_h(info["token"]),
        json={"abstract": "Updated abstract."},
    )
    assert resp.status_code == 200
    stored = mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": pub["publication_id"]}
    )
    assert stored["abstract"] == "Updated abstract."


def test_faculty_profile_update_persists(client):
    info = _register_faculty(client)
    resp = client.put(
        "/api/faculty/profile",
        headers=_h(info["token"]),
        json={"designation": "Associate Professor", "research_interests": "Testing"},
    )
    assert resp.status_code == 200
    faculty = mongodb.get_collection(FACULTY).find_one(
        {"faculty_id": info["faculty_id"]}
    )
    assert faculty["designation"] == "Associate Professor"


# --- 8. Document metadata + extraction persistence ---------------------------

def test_document_metadata_and_extraction_persist(client):
    _seed()
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = client.post(
        f"/api/publications/{pub['publication_id']}/documents",
        headers=_h(info["token"]),
        data={"document_type": "research_paper"},
        files={"file": ("integration.pdf", _make_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    doc_id = body["id"]
    assert "storage_path" not in body

    stored = mongodb.get_collection(DOCUMENTS).find_one({"document_id": doc_id})
    assert stored is not None
    assert stored["publication_id"] == pub["publication_id"]
    assert stored["faculty_id"] == info["faculty_id"]
    assert stored["checksum"]
    assert all(not isinstance(v, (bytes, bytearray)) for v in stored.values())

    proc = client.post(
        f"/api/publications/{pub['publication_id']}/documents/{doc_id}/process",
        headers=_h(info["token"]),
    )
    assert proc.status_code == 200
    assert proc.json()["processing_status"] == "processed"
    content = mongodb.get_collection(DOCUMENT_CONTENTS).find_one(
        {"document_id": doc_id}
    )
    assert content is not None and content["text_length"] > 0
    assert content["pages"][0]["page_number"] == 1


# --- 9-11. Verification, points, reports persistence -------------------------

def test_verification_points_and_reports_persist(client):
    _seed()
    admin_token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    pid = pub["publication_id"]

    verify = client.post(
        f"/api/admin/publications/{pid}/verification",
        headers=_h(admin_token),
        json={"action": "verify"},
    )
    assert verify.status_code == 200
    record = mongodb.get_collection(VERIFICATION_RECORDS).find_one(
        {"publication_id": pid, "action": "verify"}
    )
    assert record is not None
    stored_pub = mongodb.get_collection(PUBLICATIONS).find_one({"publication_id": pid})
    assert stored_pub["verification_status"] == "verified"
    year_id = stored_pub["academic_year_id"]

    recalc = client.post(
        "/api/points/recalculate",
        headers=_h(info["token"]),
        json={"academic_year_id": year_id},
    )
    assert recalc.status_code == 200
    assert recalc.json()["total_points"] >= 100
    points = mongodb.get_collection(FACULTY_POINTS).find_one(
        {"faculty_id": info["faculty_id"], "academic_year_id": year_id}
    )
    assert points is not None

    listing = client.get(
        f"/api/publications?academic_year_id={year_id}&page_size=100",
        headers=_h(info["token"]),
    )
    assert listing.status_code == 200
    assert any(
        item["publication_id"] == pid for item in listing.json()["items"]
    )


# --- 12-13. Ownership & admin authorization ----------------------------------

def test_cross_faculty_access_denied(client):
    _seed()
    a = _register_faculty(client)
    b = _register_faculty(client)
    pub = _create_publication(client, a["token"])
    pid = pub["publication_id"]
    assert client.get(f"/api/publications/{pid}", headers=_h(b["token"])).status_code in (403, 404)
    assert client.get(
        f"/api/publications/{pid}/documents", headers=_h(b["token"])
    ).status_code in (403, 404)


def test_admin_authorization_enforced(client):
    _seed()
    faculty = _register_faculty(client)
    pub = _create_publication(client, faculty["token"])
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(faculty["token"]),
        json={"action": "verify"},
    )
    assert resp.status_code == 403
    assert client.get("/api/admin/summary").status_code == 401


# --- RAG persistence & retrieval ownership (Step 15A/15B) --------------------

def test_rag_chunks_persist_and_retrieval_is_scoped(client):
    _seed()
    a = _register_faculty(client)
    b = _register_faculty(client)
    pub_a = _create_publication(client, a["token"], title="RAG A")
    pub_b = _create_publication(client, b["token"], title="RAG B")

    def upload(token, pid, text):
        resp = client.post(
            f"/api/publications/{pid}/documents",
            headers=_h(token),
            data={"document_type": "research_paper"},
            files={"file": ("rag.pdf", _make_pdf(text), "application/pdf")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["id"]
        proc = client.post(
            f"/api/publications/{pid}/documents/{doc_id}/knowledge/process",
            headers=_h(token),
        )
        assert proc.status_code == 200 and proc.json()["rag_status"] == "completed", proc.text
        return doc_id

    doc_a = upload(a["token"], pub_a["publication_id"], "quantum entanglement interferometry study")
    doc_b = upload(b["token"], pub_b["publication_id"], "custard pastry baking methods")

    stored = mongodb.get_collection(DOCUMENT_CHUNKS).find_one({"document_id": doc_a})
    assert stored is not None and stored.get("embedding") and stored["faculty_id"] == a["faculty_id"]

    res_a = client.post(
        "/api/rag/retrieve", headers=_h(a["token"]), json={"query": "quantum interferometry"}
    )
    assert res_a.status_code == 200
    ids = {r["document_id"] for r in res_a.json()["results"]}
    assert doc_a in ids and doc_b not in ids

    blocked = client.post(
        "/api/rag/retrieve",
        headers=_h(a["token"]),
        json={"query": "custard", "document_id": doc_b},
    )
    assert blocked.status_code == 403

    deleted = client.delete(
        f"/api/publications/{pub_b['publication_id']}/documents/{doc_b}",
        headers=_h(b["token"]),
    )
    assert deleted.status_code == 204
    assert mongodb.get_collection(DOCUMENT_CHUNKS).count_documents({"document_id": doc_b}) == 0


# --- 14. CORS for the browser dev origin -------------------------------------

def test_cors_preflight_allows_dev_origin(client):
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


def test_cors_rejects_unknown_origin(client):
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://malicious.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") in (None, "")
