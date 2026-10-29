"""Scopus / Elsevier integration tests (Step 10)."""

import itertools
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.database import mongodb
from app.integrations.scopus import ScopusClient
from app.models.collections import ACADEMIC_YEARS, USERS
from app.services import author_matching_service, scopus_service
from app.utils import security

PASSWORD = "StrongPassword123"

SCOPUS_EID = "2-s2.0-85123456789"
SCOPUS_AUTHOR_ID = "123456"

SCOPUS_SEARCH = {
    "search-results": {
        "opensearch:totalResults": "1",
        "entry": [
            {
                "eid": SCOPUS_EID,
                "dc:title": "Machine Learning in Education",
                "dc:creator": "Sakshi Priya; Jane Doe",
                "prism:coverDate": "2025-08-15",
                "prism:publicationName": "Journal of AI",
                "prism:doi": "10.1016/scopus",
                "prism:issn": "1234-5678",
                "dc:description": "Abstract text",
                "dc:identifier": "SCOPUS_ID:85123456789",
                "author": [
                    {
                        "authid": SCOPUS_AUTHOR_ID,
                        "given-name": "Sakshi",
                        "surname": "Priya",
                        "affiliation": [{"affilname": "BV University"}],
                    }
                ],
            }
        ],
    }
}

SCOPUS_ABSTRACT = {
    "abstracts-retrieval-response": {
        "coredata": {
            "eid": SCOPUS_EID,
            "dc:title": "Machine Learning in Education",
            "prism:coverDate": "2025-08-15",
            "prism:publicationName": "Journal of AI",
            "prism:doi": "10.1016/scopus",
            "dc:description": "Abstract text",
            "dc:identifier": "SCOPUS_ID:85123456789",
            "scopus-id": "85123456789",
        },
        "authors": {
            "author": [
                {
                    "@auid": SCOPUS_AUTHOR_ID,
                    "ce:given-name": "Sakshi",
                    "ce:surname": "Priya",
                    "affiliation": {"affilname": "BV University"},
                }
            ]
        },
    }
}

SCOPUS_AUTHOR = {
    "author-retrieval-response": [
        {
            "author": {
                "@authid": SCOPUS_AUTHOR_ID,
                "author-name": {"given-name": "Sakshi", "surname": "Priya"},
                "subject-area": [{"$": "Computer Science"}],
            }
        }
    ]
}


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        if self._json is None:
            raise ValueError("invalid json")
        return self._json


def _scopus_handler(url, **kwargs):
    if "/search/scopus" in url:
        return _FakeResponse(SCOPUS_SEARCH)
    if "/abstract/eid/" in url:
        return _FakeResponse(SCOPUS_ABSTRACT)
    if "/author/author_id/" in url:
        return _FakeResponse(SCOPUS_AUTHOR)
    raise AssertionError(f"unexpected url: {url}")


def _no_key(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.scopus.get_settings",
        lambda: SimpleNamespace(
            scopus_api_url="https://api.elsevier.com/content",
            scopus_timeout_seconds=10.0,
            scopus_api_key=None,
        ),
    )


@pytest.fixture(autouse=True)
def _seed(client):
    _ensure_academic_year("2025-2026")
    yield


def _ensure_academic_year(name="2025-2026"):
    db = mongodb.get_database()
    if db[ACADEMIC_YEARS].find_one({"name": name}) is None:
        db[ACADEMIC_YEARS].insert_one(
            {
                "academic_year_id": str(uuid.uuid4()),
                "name": name,
                "start_date": "2025-07-01",
                "end_date": "2026-06-30",
                "is_current": True,
            }
        )


_scopus_counter = itertools.count(100000)


def _register_faculty(client, scopus_id=None, orcid=None, name="Sakshi Priya") -> dict:
    email = f"sco_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": name,
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    profile = {}
    if scopus_id:
        profile["scopus_author_id"] = scopus_id
    if orcid:
        profile["orcid_id"] = orcid
    if profile:
        client.put("/api/faculty/profile", headers=_h(token), json=profile)
    return {"email": email, "token": token, "faculty_id": reg.json()["faculty_id"]}


def _admin_token(client) -> str:
    email = f"admin_{uuid.uuid4().hex[:10]}@example.com"
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


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# --- Configuration -----------------------------------------------------------

def test_missing_api_key(monkeypatch):
    _no_key(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("query")
    assert exc.value.status_code == 503


def test_api_key_never_in_response(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    info = _register_faculty(client)
    resp = client.get("/api/scopus/search?query=x", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert "test-scopus-api-key" not in resp.text


# --- Search ------------------------------------------------------------------

def test_scopus_search(monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    result = scopus_service.search_scopus("machine learning")
    assert result["total"] == 1
    record = result["results"][0]
    assert record.source == "scopus"
    assert record.source_record_id == SCOPUS_EID
    assert record.title == "Machine Learning in Education"
    assert record.doi == "10.1016/scopus"
    assert record.journal == "Journal of AI"
    assert record.publication_year == 2025
    assert record.indexing == ["Scopus"]


def test_scopus_normalization(monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    record = scopus_service.get_publication(SCOPUS_EID)
    assert record.authors[0].name == "Sakshi Priya"
    assert record.authors[0].scopus_author_id == SCOPUS_AUTHOR_ID
    assert record.authors[0].affiliation == ["BV University"]
    assert record.external_identifiers["eid"] == SCOPUS_EID
    assert record.external_identifiers["scopus_id"] == "85123456789"


def test_scopus_author(monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    author = scopus_service.get_author(SCOPUS_AUTHOR_ID)
    assert author.author_id == SCOPUS_AUTHOR_ID
    assert author.given_name == "Sakshi"
    assert author.family_name == "Priya"


def test_scopus_empty_results(monkeypatch):
    monkeypatch.setattr(
        "httpx.get",
        lambda url, **kw: _FakeResponse(
            {"search-results": {"opensearch:totalResults": "0", "entry": []}}
        ),
    )
    result = scopus_service.search_scopus("xyz")
    assert result["total"] == 0
    assert result["results"] == []


def test_scopus_malformed(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(json_data=None))
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("x")
    assert exc.value.status_code == 502


def test_scopus_timeout(monkeypatch):
    def raise_timeout(url, **kw):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("httpx.get", raise_timeout)
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("x")
    assert exc.value.status_code == 504


def test_scopus_401(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=401))
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("x")
    assert exc.value.status_code == 401


def test_scopus_403(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=403))
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("x")
    assert exc.value.status_code == 401


def test_scopus_404(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=404))
    with pytest.raises(HTTPException) as exc:
        scopus_service.get_publication("bad-eid")
    assert exc.value.status_code == 404


def test_scopus_429(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=429))
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("x")
    assert exc.value.status_code == 429


def test_scopus_5xx(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=500))
    with pytest.raises(HTTPException) as exc:
        scopus_service.search_scopus("x")
    assert exc.value.status_code == 502


# --- Author matching ---------------------------------------------------------

def test_scopus_author_id_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "scopus_author_id": SCOPUS_AUTHOR_ID},
        {"name": "Sakshi Priya", "scopus_author_id": SCOPUS_AUTHOR_ID},
    )
    assert result["matched"] is True
    assert result["confidence"] == "high"
    assert "scopus_author_id" in result["matching_factors"]


def test_scopus_orcid_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "orcid_id": "0000-0002-1825-0097"},
        {"name": "Sakshi Priya", "orcid_id": "0000-0002-1825-0097"},
    )
    assert result["confidence"] == "high"
    assert "orcid_id" in result["matching_factors"]


def test_scopus_name_only_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya"}, {"name": "Sakshi Priya"}
    )
    assert result["matched"] is True
    assert result["confidence"] == "medium"


def test_scopus_mismatch():
    result = author_matching_service.match_author(
        {"name": "Someone Else", "scopus_author_id": "999999"},
        {"name": "Sakshi Priya", "scopus_author_id": SCOPUS_AUTHOR_ID},
    )
    assert result["confidence"] == "low"


# --- API ---------------------------------------------------------------------

def test_unauthenticated_401(client):
    resp = client.get("/api/scopus/search?query=x")
    assert resp.status_code == 401


def test_faculty_search_success(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    info = _register_faculty(client)
    resp = client.get("/api/scopus/search?query=x", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_admin_search_success(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    token = _admin_token(client)
    resp = client.get("/api/scopus/search?query=x", headers=_h(token))
    assert resp.status_code == 200


def test_invalid_pagination_400(client):
    info = _register_faculty(client)
    resp = client.get(
        "/api/scopus/search", params={"query": "x", "page_size": 100}, headers=_h(info["token"])
    )
    assert resp.status_code == 400


def test_empty_query_400(client):
    info = _register_faculty(client)
    resp = client.get("/api/scopus/search", headers=_h(info["token"]))
    assert resp.status_code == 400


def test_scopus_via_search_external(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/search-external",
        params={"source": "scopus", "query": "x"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "scopus"
    assert resp.json()["total"] == 1


# --- Import ------------------------------------------------------------------

def _import_payload(**overrides) -> dict:
    uid = uuid.uuid4().hex[:8]
    sid = str(next(_scopus_counter))
    payload = {
        "source": "scopus",
        "source_record_id": f"2-s2.0-{uuid.uuid4().hex[:8]}",
        "title": "Machine Learning in Education",
        "authors": [{"name": "Sakshi Priya", "scopus_author_id": sid}],
        "doi": f"10.1016/{uid}",
        "publication_date": "2025-08-15",
        "journal": "Journal of AI",
        "indexing": ["Scopus"],
    }
    payload.update(overrides)
    return payload


def test_import_scopus_high_confidence(client):
    sid = str(next(_scopus_counter))
    info = _register_faculty(client, scopus_id=sid)
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(authors=[{"name": "Sakshi Priya", "scopus_author_id": sid}]),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "scopus"
    assert body["verification_status"] == "pending"
    assert body["points_awarded"] == 0
    assert body["faculty_id"] == info["faculty_id"]
    assert body["publication_year"] == 2025


def test_import_scopus_missing_confirmation_400(client):
    info = _register_faculty(client, name="Jane Other")
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(),
    )
    assert resp.status_code == 400


def test_import_scopus_confirmed(client):
    info = _register_faculty(client, name="Jane Other")
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(author_match_confirmed=True),
    )
    assert resp.status_code == 201


def test_import_scopus_duplicate_doi_409(client):
    sid = str(next(_scopus_counter))
    info = _register_faculty(client, scopus_id=sid)
    authors = [{"name": "Sakshi Priya", "scopus_author_id": sid}]
    payload = _import_payload(authors=authors)
    assert (
        client.post(
            "/api/publications/import-external", headers=_h(info["token"]), json=payload
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(doi=payload["doi"], source_record_id="2-s2.0-OTHER", authors=authors),
    )
    assert resp.status_code == 409


def test_import_scopus_duplicate_source_record_409(client):
    sid = str(next(_scopus_counter))
    info = _register_faculty(client, scopus_id=sid)
    authors = [{"name": "Sakshi Priya", "scopus_author_id": sid}]
    payload = _import_payload(authors=authors)
    assert (
        client.post(
            "/api/publications/import-external", headers=_h(info["token"]), json=payload
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(
            source_record_id=payload["source_record_id"],
            doi=f"10.2020/{uuid.uuid4().hex[:8]}",
            authors=authors,
        ),
    )
    assert resp.status_code == 409


# --- Author ID search --------------------------------------------------------

def test_scopus_author_id_query_builds_auid():
    assert ScopusClient._build_query("", None, None, None, "58644291200") == "AU-ID(58644291200)"
    # Author ID takes precedence over an author name.
    assert ScopusClient._build_query("", None, "Jane Doe", None, "58644291200") == "AU-ID(58644291200)"
    assert ScopusClient._build_query("", None, "Jane Doe", None, None) == "AUTH(Jane Doe)"
    assert ScopusClient._build_query("free text", None, None, None, None) == "free text"


def test_scopus_search_by_author_id(client, monkeypatch):
    captured = {}

    def handler(url, **kwargs):
        if "/search/scopus" in url:
            captured["params"] = kwargs.get("params")
            return _FakeResponse(SCOPUS_SEARCH)
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("httpx.get", handler)
    info = _register_faculty(client)
    resp = client.get("/api/scopus/search?author_id=58644291200", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert captured["params"]["query"] == "AU-ID(58644291200)"


def test_scopus_author_id_empty_query_allowed(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _scopus_handler)
    info = _register_faculty(client)
    # No query, only an author_id — should not be rejected as empty.
    resp = client.get("/api/scopus/search?author_id=58644291200", headers=_h(info["token"]))
    assert resp.status_code == 200
