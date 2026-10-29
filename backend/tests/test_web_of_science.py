"""Web of Science / Clarivate integration tests (Step 11)."""

import itertools
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, USERS
from app.services import author_matching_service, web_of_science_service
from app.utils import security

PASSWORD = "StrongPassword123"

WOS_UID = "WOS:000123456789012"
WOS_RID = "A-1234-2020"

WOS_DOC = {
    "uid": WOS_UID,
    "title": "Machine Learning in Education",
    "types": ["Article"],
    "source": {
        "sourceTitle": "Journal of AI",
        "publisher": "Wiley",
        "issn": "1234-5678",
        "publishYear": 2025,
        "publishMonth": 8,
        "publishDay": 15,
    },
    "names": {
        "authors": [
            {
                "displayName": "Sakshi Priya",
                "researcherId": WOS_RID,
                "orcid": "0000-0002-1825-0097",
                "wosStandard": {"firstName": "Sakshi", "lastName": "Priya"},
                "addresses": [{"address": "BV University"}],
            }
        ]
    },
    "identifiers": {"doi": "10.1002/wos", "issn": "1234-5678"},
    "links": {"record": "https://www.webofscience.com/wos/woscc/full-record/WOS:000123456789012"},
    "citations": [{"db": "WOS", "count": 10}],
}

WOS_SEARCH = {"metadata": {"total": 1, "page": 1, "limit": 10}, "hits": [WOS_DOC]}


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        if self._json is None:
            raise ValueError("invalid json")
        return self._json


def _wos_handler(url, **kwargs):
    if "/documents/" in url:
        return _FakeResponse(WOS_DOC)
    if "/documents" in url:
        return _FakeResponse(WOS_SEARCH)
    raise AssertionError(f"unexpected url: {url}")


def _no_key(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.web_of_science.get_settings",
        lambda: SimpleNamespace(
            web_of_science_api_url="https://api.clarivate.com/apis/wos-starter/v1",
            web_of_science_timeout_seconds=10.0,
            web_of_science_api_key=None,
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


_rid_counter = itertools.count(1)


def _unique_rid() -> str:
    n = next(_rid_counter)
    return f"A-{n:04d}-2020"


def _register_faculty(client, researcher_id=None, orcid=None, name="Sakshi Priya") -> dict:
    email = f"wos_{uuid.uuid4().hex[:10]}@example.com"
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
    if researcher_id:
        profile["web_of_science_researcher_id"] = researcher_id
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
        web_of_science_service.search_web_of_science("query")
    assert exc.value.status_code == 503


def test_api_key_never_in_response(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    info = _register_faculty(client)
    resp = client.get("/api/web-of-science/search?query=x", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert "test-wos-api-key" not in resp.text


# --- Search ------------------------------------------------------------------

def test_wos_search(monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    result = web_of_science_service.search_web_of_science("machine learning")
    assert result["total"] == 1
    record = result["results"][0]
    assert record.source == "web_of_science"
    assert record.source_record_id == WOS_UID
    assert record.title == "Machine Learning in Education"
    assert record.doi == "10.1002/wos"
    assert record.journal == "Journal of AI"
    assert record.indexing == ["Web of Science"]


def test_wos_normalization(monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    record = web_of_science_service.get_publication(WOS_UID)
    assert record.authors[0].name == "Sakshi Priya"
    assert record.authors[0].web_of_science_researcher_id == WOS_RID
    assert record.authors[0].orcid_id == "0000-0002-1825-0097"
    assert record.authors[0].affiliation == ["BV University"]
    assert record.external_identifiers["ut"] == WOS_UID
    assert record.publication_year == 2025


def test_wos_researcher_not_supported(monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.get_researcher(WOS_RID)
    assert exc.value.status_code == 501


def test_wos_empty_results(monkeypatch):
    monkeypatch.setattr(
        "httpx.get",
        lambda url, **kw: _FakeResponse({"metadata": {"total": 0}, "hits": []}),
    )
    result = web_of_science_service.search_web_of_science("xyz")
    assert result["total"] == 0
    assert result["results"] == []


def test_wos_malformed(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(json_data=None))
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.search_web_of_science("x")
    assert exc.value.status_code == 502


def test_wos_timeout(monkeypatch):
    def raise_timeout(url, **kw):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("httpx.get", raise_timeout)
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.search_web_of_science("x")
    assert exc.value.status_code == 504


def test_wos_401(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=401))
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.search_web_of_science("x")
    assert exc.value.status_code == 401


def test_wos_403(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=403))
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.search_web_of_science("x")
    assert exc.value.status_code == 401


def test_wos_404(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=404))
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.get_publication("WOS:bad")
    assert exc.value.status_code == 404


def test_wos_429(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=429))
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.search_web_of_science("x")
    assert exc.value.status_code == 429


def test_wos_5xx(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=500))
    with pytest.raises(HTTPException) as exc:
        web_of_science_service.search_web_of_science("x")
    assert exc.value.status_code == 502


# --- Author matching ---------------------------------------------------------

def test_wos_researcher_id_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "web_of_science_researcher_id": WOS_RID},
        {"name": "Sakshi Priya", "web_of_science_researcher_id": WOS_RID},
    )
    assert result["matched"] is True
    assert result["confidence"] == "high"
    assert "web_of_science_researcher_id" in result["matching_factors"]


def test_wos_orcid_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "orcid_id": "0000-0002-1825-0097"},
        {"name": "Sakshi Priya", "orcid_id": "0000-0002-1825-0097"},
    )
    assert result["confidence"] == "high"


def test_wos_name_only_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya"}, {"name": "Sakshi Priya"}
    )
    assert result["confidence"] == "medium"


def test_wos_mismatch():
    result = author_matching_service.match_author(
        {"name": "Someone Else", "web_of_science_researcher_id": "B-9999-2020"},
        {"name": "Sakshi Priya", "web_of_science_researcher_id": WOS_RID},
    )
    assert result["confidence"] == "low"


# --- API ---------------------------------------------------------------------

def test_unauthenticated_401(client):
    resp = client.get("/api/web-of-science/search?query=x")
    assert resp.status_code == 401


def test_faculty_search_success(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    info = _register_faculty(client)
    resp = client.get("/api/web-of-science/search?query=x", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_admin_search_success(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    token = _admin_token(client)
    resp = client.get("/api/web-of-science/search?query=x", headers=_h(token))
    assert resp.status_code == 200


def test_invalid_pagination_400(client):
    info = _register_faculty(client)
    resp = client.get(
        "/api/web-of-science/search",
        params={"query": "x", "page_size": 100},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 400


def test_empty_query_400(client):
    info = _register_faculty(client)
    resp = client.get("/api/web-of-science/search", headers=_h(info["token"]))
    assert resp.status_code == 400


def test_wos_via_search_external(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _wos_handler)
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/search-external",
        params={"source": "web_of_science", "query": "x"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "web_of_science"
    assert resp.json()["total"] == 1


# --- Import ------------------------------------------------------------------

def _import_payload(**overrides) -> dict:
    uid = uuid.uuid4().hex[:8]
    rid = _unique_rid()
    payload = {
        "source": "web_of_science",
        "source_record_id": f"WOS:{uuid.uuid4().hex[:12]}",
        "title": "Machine Learning in Education",
        "authors": [{"name": "Sakshi Priya", "web_of_science_researcher_id": rid}],
        "doi": f"10.1002/{uid}",
        "publication_date": "2025-08-15",
        "journal": "Journal of AI",
        "indexing": ["Web of Science"],
    }
    payload.update(overrides)
    return payload


def test_import_wos_high_confidence(client):
    rid = _unique_rid()
    info = _register_faculty(client, researcher_id=rid)
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(
            authors=[{"name": "Sakshi Priya", "web_of_science_researcher_id": rid}]
        ),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "web_of_science"
    assert body["verification_status"] == "pending"
    assert body["points_awarded"] == 0
    assert body["faculty_id"] == info["faculty_id"]
    assert body["publication_year"] == 2025


def test_import_wos_missing_confirmation_400(client):
    info = _register_faculty(client, name="Jane Other")
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(),
    )
    assert resp.status_code == 400


def test_import_wos_confirmed(client):
    info = _register_faculty(client, name="Jane Other")
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(author_match_confirmed=True),
    )
    assert resp.status_code == 201


def test_import_wos_duplicate_doi_409(client):
    rid = _unique_rid()
    info = _register_faculty(client, researcher_id=rid)
    authors = [{"name": "Sakshi Priya", "web_of_science_researcher_id": rid}]
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
        json=_import_payload(doi=payload["doi"], source_record_id="WOS:OTHER", authors=authors),
    )
    assert resp.status_code == 409


def test_import_wos_duplicate_source_record_409(client):
    rid = _unique_rid()
    info = _register_faculty(client, researcher_id=rid)
    authors = [{"name": "Sakshi Priya", "web_of_science_researcher_id": rid}]
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
            doi=f"10.2000/{uuid.uuid4().hex[:8]}",
            authors=authors,
        ),
    )
    assert resp.status_code == 409
