"""Unified research-publication search tests (faculty + admin)."""

import uuid
from types import SimpleNamespace

from fastapi import HTTPException

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, PUBLICATIONS, USERS
from app.services import research_search_service
from app.utils import security

PASSWORD = "StrongPassword123"


def _ensure_year(name="2025-2026"):
    db = mongodb.get_database()
    if db[ACADEMIC_YEARS].find_one({"name": name}) is None:
        start = int(name.split("-")[0])
        db[ACADEMIC_YEARS].insert_one(
            {
                "academic_year_id": str(uuid.uuid4()),
                "name": name,
                "start_date": f"{start}-07-01",
                "end_date": f"{start + 1}-06-30",
                "is_current": False,
            }
        )


def _admin_token(client):
    email = f"rs_admin_{uuid.uuid4().hex[:8]}@example.com"
    mongodb.get_collection(USERS).insert_one(
        {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password_hash": security.hash_password(PASSWORD),
            "role": "admin",
            "faculty_id": None,
            "is_active": True,
            "approval_status": "approved",
        }
    )
    return client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]


def _register(client, name="Search Faculty"):
    email = f"rs_{uuid.uuid4().hex[:8]}@example.com"
    employee_id = "EMP_" + uuid.uuid4().hex[:6]
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": name,
            "employee_id": employee_id,
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {
        "email": email,
        "token": token,
        "faculty_id": reg.json()["faculty_id"],
        "employee_id": employee_id,
    }


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_publication(client, token, title="A Publication", authors=None, doi=None):
    _ensure_year()
    payload = {
        "title": title,
        "authors": authors or ["Sakshi Priya"],
        "publication_type": "research_publication",
        "faculty_author_position": 1,
        "publication_date": "2025-08-15",
        "indexing": ["Scopus"],
    }
    if doi:
        payload["doi"] = doi
    resp = client.post("/api/publications", headers=_h(token), json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Faculty ID / Employee ID lookup ----------------------------------------

def test_faculty_search_returns_own_publications(client):
    info = _register(client)
    _create_publication(client, info["token"], title="My Internal Paper")
    resp = client.get("/api/search/research", params={"type": "faculty"}, headers=_h(info["token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(r["title"] == "My Internal Paper" and r["kind"] == "internal" for r in body["results"])


def test_admin_can_search_faculty_by_employee_id(client):
    admin = _admin_token(client)
    info = _register(client, name="Target Faculty")
    _create_publication(client, info["token"], title="Target Paper")
    resp = client.get(
        "/api/search/research",
        params={"type": "faculty", "q": info["employee_id"]},
        headers=_h(admin),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(r["title"] == "Target Paper" for r in body["results"])
    result = next(r for r in body["results"] if r["title"] == "Target Paper")
    assert result["faculty_id"] == info["faculty_id"]
    assert result["faculty_name"] == "Target Faculty"


def test_admin_faculty_search_requires_identifier(client):
    admin = _admin_token(client)
    resp = client.get("/api/search/research", params={"type": "faculty"}, headers=_h(admin))
    assert resp.status_code == 400


def test_faculty_type_not_found_for_admin(client):
    admin = _admin_token(client)
    resp = client.get(
        "/api/search/research",
        params={"type": "faculty", "q": "no-such-id"},
        headers=_h(admin),
    )
    assert resp.status_code == 404


# --- Scopus Author ID --------------------------------------------------------

def test_scopus_author_search_returns_external(client, monkeypatch):
    info = _register(client)
    monkeypatch.setattr(
        research_search_service,
        "scopus_service",
        SimpleNamespace(
            search_scopus=lambda **kw: {
                "total": 1,
                "results": [
                    {
                        "source": "scopus",
                        "source_record_id": "eid-1",
                        "title": "Scopus Work",
                        "doi": "10.2/scopus",
                        "authors": [{"name": "Sakshi Priya"}],
                        "external_identifiers": {"scopus_id": "123"},
                    }
                ],
            }
        ),
    )
    resp = client.get(
        "/api/search/research",
        params={"type": "scopus_author", "q": "58644291200"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["kind"] == "external"
    assert result["importable"] is True
    assert result["title"] == "Scopus Work"


def test_scopus_author_missing_key(client, monkeypatch):
    info = _register(client)

    def _boom(**kw):
        raise HTTPException(status_code=503, detail="Scopus API key is not configured")

    monkeypatch.setattr(
        research_search_service, "scopus_service", SimpleNamespace(search_scopus=_boom)
    )
    resp = client.get(
        "/api/search/research",
        params={"type": "scopus_author", "q": "58644291200"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"]


def test_scopus_author_empty_query_rejected(client):
    info = _register(client)
    resp = client.get(
        "/api/search/research", params={"type": "scopus_author"}, headers=_h(info["token"])
    )
    assert resp.status_code == 400


# --- ORCID -------------------------------------------------------------------

def test_orcid_search_returns_external(client, monkeypatch):
    info = _register(client)

    class _FakeOrcid:
        def get_works(self, orcid, page=1, page_size=10):
            return {
                "total": 1,
                "results": [
                    {
                        "source": "orcid",
                        "source_record_id": "1",
                        "title": "ORCID Work",
                        "doi": "10.3/orcid",
                        "external_identifiers": {"orcid": orcid},
                    }
                ],
            }

    monkeypatch.setattr(research_search_service, "OrcidClient", _FakeOrcid)
    resp = client.get(
        "/api/search/research",
        params={"type": "orcid", "q": "https://orcid.org/0000-0002-1825-0097"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["title"] == "ORCID Work"


def test_orcid_invalid_identifier_rejected(client):
    info = _register(client)
    resp = client.get(
        "/api/search/research", params={"type": "orcid", "q": "not-an-orcid"}, headers=_h(info["token"])
    )
    assert resp.status_code == 400


# --- Author name / DOI / title ----------------------------------------------

def test_author_name_internal_search_scoped(client):
    a = _register(client, name="Alice")
    b = _register(client, name="Bob")
    _create_publication(client, a["token"], title="Alice Paper", authors=["Alice Smith"])
    _create_publication(client, b["token"], title="Bob Paper", authors=["Bob Jones"])

    resp = client.get(
        "/api/search/research",
        params={"type": "author_name", "q": "Smith"},
        headers=_h(a["token"]),
    )
    assert resp.status_code == 200
    titles = {r["title"] for r in resp.json()["results"]}
    assert "Alice Paper" in titles
    assert "Bob Paper" not in titles


def test_doi_and_title_internal_search(client):
    info = _register(client)
    _create_publication(client, info["token"], title="Unique Title 123", doi="10.9/unique")

    doi_resp = client.get(
        "/api/search/research", params={"type": "doi", "q": "10.9/unique"}, headers=_h(info["token"])
    )
    assert any(r["title"] == "Unique Title 123" for r in doi_resp.json()["results"])

    title_resp = client.get(
        "/api/search/research", params={"type": "title", "q": "Unique Title"}, headers=_h(info["token"])
    )
    assert any(r["title"] == "Unique Title 123" for r in title_resp.json()["results"])


def test_author_name_with_external_source(client, monkeypatch):
    info = _register(client)
    monkeypatch.setattr(
        research_search_service.external_publication_service,
        "search_external",
        lambda **kw: {
            "total": 1,
            "results": [
                {"source": "crossref", "source_record_id": "c1", "title": "Ext Paper",
                 "authors": [{"name": "Sakshi Priya"}]}
            ],
        },
    )
    resp = client.get(
        "/api/search/research",
        params={"type": "author_name", "q": "Priya", "source": "crossref"},
        headers=_h(info["token"]),
    )
    kinds = {r["kind"] for r in resp.json()["results"]}
    assert "external" in kinds


# --- Authorization & validation ---------------------------------------------

def test_unauthenticated_rejected(client):
    resp = client.get("/api/search/research", params={"type": "faculty"})
    assert resp.status_code == 401


def test_invalid_search_type_rejected(client):
    info = _register(client)
    resp = client.get(
        "/api/search/research", params={"type": "bogus", "q": "x"}, headers=_h(info["token"])
    )
    assert resp.status_code == 400


def test_internal_results_are_not_importable(client):
    info = _register(client)
    _create_publication(client, info["token"], title="Internal")
    resp = client.get(
        "/api/search/research", params={"type": "title", "q": "Internal"}, headers=_h(info["token"])
    )
    result = next(r for r in resp.json()["results"] if r["title"] == "Internal")
    assert result["kind"] == "internal"
    assert result["importable"] is False
    assert result["verification_status"] == "pending"


def test_admin_internal_search_across_all(client):
    admin = _admin_token(client)
    a = _register(client, name="Alice")
    b = _register(client, name="Bob")
    _create_publication(client, a["token"], title="Alice Title")
    _create_publication(client, b["token"], title="Bob Title")
    resp = client.get(
        "/api/search/research", params={"type": "title", "q": "Title"}, headers=_h(admin)
    )
    titles = {r["title"] for r in resp.json()["results"]}
    assert "Alice Title" in titles and "Bob Title" in titles
    result = next(r for r in resp.json()["results"] if r["title"] == "Alice Title")
    assert result["faculty_name"] == "Alice"
