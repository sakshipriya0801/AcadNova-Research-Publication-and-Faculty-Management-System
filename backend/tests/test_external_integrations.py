"""External source integration tests (Step 8B)."""

import uuid

import httpx
import pytest
from fastapi import HTTPException

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, PUBLICATIONS, USERS
from app.services import external_publication_service
from app.utils import security
from scripts.seed_rules import seed_eligibility_rules, seed_publication_rules

PASSWORD = "StrongPassword123"

CROSSREF_ITEM = {
    "DOI": "10.1234/example",
    "title": ["Machine Learning in Education"],
    "author": [
        {"given": "Jane", "family": "Doe", "affiliation": [{"name": "Example University"}]},
    ],
    "container-title": ["Example Journal"],
    "publisher": "Example Publisher",
    "published": {"date-parts": [[2025, 8, 15]]},
    "URL": "https://doi.org/10.1234/example",
    "abstract": "<jats:p>Example abstract.</jats:p>",
    "type": "journal-article",
    "ISSN": ["1234-5678"],
}

CROSSREF_RESPONSE = {"message": {"total-results": 1, "items": [CROSSREF_ITEM]}}

ESEARCH_RESPONSE = {"esearchresult": {"count": "1", "idlist": ["12345678"]}}
ESUMMARY_RESPONSE = {
    "result": {
        "uids": ["12345678"],
        "12345678": {
            "title": "AI in medicine",
            "authors": [{"name": "Smith J"}],
            "source": "J Med",
            "fulljournalname": "Journal of Medicine",
            "pubdate": "2025 Aug 15",
            "articleids": [{"idtype": "doi", "value": "10.9999/pubmed"}],
        },
    }
}


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        if self._json is None:
            raise ValueError("invalid json")
        return self._json


def _pubmed_handler(url, **kwargs):
    if "esearch" in url:
        return _FakeResponse(ESEARCH_RESPONSE)
    if "esummary" in url:
        return _FakeResponse(ESUMMARY_RESPONSE)
    raise AssertionError(f"unexpected url: {url}")


@pytest.fixture(autouse=True)
def _seed(client):
    seed_publication_rules()
    seed_eligibility_rules()
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


def _register_faculty(client) -> dict:
    email = f"ext_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Ext Faculty",
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
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


def _import_payload(**overrides) -> dict:
    uid = uuid.uuid4().hex[:8]
    payload = {
        "source": "crossref",
        "source_record_id": f"10.1000/{uid}",
        "title": "Imported Paper",
        "authors": [{"name": "Jane Doe"}],
        "doi": f"10.1000/{uid}",
        "publication_date": "2025-08-15",
        "journal": "Example Journal",
        "indexing": [],
    }
    payload.update(overrides)
    return payload


# --- Crossref client ---------------------------------------------------------

def test_crossref_search(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(CROSSREF_RESPONSE))
    result = external_publication_service.search_external("crossref", "machine learning")

    assert result["total"] == 1
    record = result["results"][0]
    assert record.source == "crossref"
    assert record.doi == "10.1234/example"
    assert record.title == "Machine Learning in Education"
    assert record.journal == "Example Journal"
    assert record.authors[0].name == "Jane Doe"
    assert record.publication_year == 2025
    assert record.publication_date == "2025-08-15"
    assert record.abstract == "Example abstract."


def test_crossref_doi_normalized(monkeypatch):
    item = dict(CROSSREF_ITEM, DOI="https://doi.org/10.1234/ABC")
    monkeypatch.setattr(
        "httpx.get", lambda url, **kw: _FakeResponse({"message": {"total-results": 1, "items": [item]}})
    )
    result = external_publication_service.search_external("crossref", "x")
    assert result["results"][0].doi == "10.1234/abc"


def test_crossref_empty_results(monkeypatch):
    monkeypatch.setattr(
        "httpx.get", lambda url, **kw: _FakeResponse({"message": {"total-results": 0, "items": []}})
    )
    result = external_publication_service.search_external("crossref", "xyz")
    assert result["total"] == 0
    assert result["results"] == []


def test_crossref_malformed_response(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(json_data=None))
    with pytest.raises(HTTPException) as exc:
        external_publication_service.search_external("crossref", "x")
    assert exc.value.status_code == 502


def test_crossref_timeout(monkeypatch):
    def raise_timeout(url, **kw):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("httpx.get", raise_timeout)
    with pytest.raises(HTTPException) as exc:
        external_publication_service.search_external("crossref", "x")
    assert exc.value.status_code == 504


def test_crossref_http_error(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=500))
    with pytest.raises(HTTPException) as exc:
        external_publication_service.search_external("crossref", "x")
    assert exc.value.status_code == 502


# --- PubMed client -----------------------------------------------------------

def test_pubmed_search(monkeypatch):
    monkeypatch.setattr("httpx.get", _pubmed_handler)
    result = external_publication_service.search_external("pubmed", "artificial intelligence")

    assert result["total"] == 1
    record = result["results"][0]
    assert record.source == "pubmed"
    assert record.source_record_id == "12345678"
    assert record.title == "AI in medicine"
    assert record.journal == "Journal of Medicine"
    assert record.doi == "10.9999/pubmed"
    assert record.indexing == ["PubMed"]
    assert record.publication_year == 2025
    assert record.url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"


def test_pubmed_empty_results(monkeypatch):
    monkeypatch.setattr(
        "httpx.get", lambda url, **kw: _FakeResponse({"esearchresult": {"count": "0", "idlist": []}})
    )
    result = external_publication_service.search_external("pubmed", "xyz")
    assert result["total"] == 0
    assert result["results"] == []


def test_pubmed_timeout(monkeypatch):
    def raise_timeout(url, **kw):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("httpx.get", raise_timeout)
    with pytest.raises(HTTPException) as exc:
        external_publication_service.search_external("pubmed", "x")
    assert exc.value.status_code == 504


def test_pubmed_http_error(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=404))
    with pytest.raises(HTTPException) as exc:
        external_publication_service.search_external("pubmed", "x")
    assert exc.value.status_code == 502


def test_pubmed_malformed_response(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(json_data=None))
    with pytest.raises(HTTPException) as exc:
        external_publication_service.search_external("pubmed", "x")
    assert exc.value.status_code == 502


def test_get_external_record_by_identifier(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse({"message": CROSSREF_ITEM}))
    record = external_publication_service.get_external_record("crossref", "10.1234/example")
    assert record.doi == "10.1234/example"
    assert record.title == "Machine Learning in Education"


# --- API ---------------------------------------------------------------------

def test_unauthenticated_search_401(client):
    resp = client.get(
        "/api/publications/search-external", params={"source": "crossref", "query": "x"}
    )
    assert resp.status_code == 401


def test_faculty_search_success(client, monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(CROSSREF_RESPONSE))
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/search-external",
        params={"source": "crossref", "query": "x"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_invalid_source_400(client):
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/search-external",
        params={"source": "google_scholar", "query": "x"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 400


def test_empty_query_400(client):
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/search-external",
        params={"source": "crossref"},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 400


def test_invalid_pagination_400(client):
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/search-external",
        params={"source": "crossref", "query": "x", "page_size": 100},
        headers=_h(info["token"]),
    )
    assert resp.status_code == 400


def test_get_external_record_api(client, monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse({"message": CROSSREF_ITEM}))
    info = _register_faculty(client)
    resp = client.get(
        "/api/publications/external/crossref/10.1234/example", headers=_h(info["token"])
    )
    assert resp.status_code == 200
    assert resp.json()["doi"] == "10.1234/example"


# --- Import ------------------------------------------------------------------

def test_import_crossref(client):
    info = _register_faculty(client)
    payload = _import_payload()
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=payload,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "crossref"
    assert body["source_record_id"] == payload["source_record_id"]
    assert body["verification_status"] == "pending"
    assert body["points_awarded"] == 0
    assert body["faculty_id"] == info["faculty_id"]
    assert body["publication_year"] == 2025


def test_import_pubmed(client):
    info = _register_faculty(client)
    uid = uuid.uuid4().hex[:8]
    payload = _import_payload(
        source="pubmed", source_record_id=uid, doi=f"10.9999/{uid}", indexing=["PubMed"]
    )
    resp = client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    )
    assert resp.status_code == 201
    assert resp.json()["source"] == "pubmed"


def test_import_faculty_id_from_jwt(client):
    info = _register_faculty(client)
    payload = _import_payload(faculty_id="HACKED")
    resp = client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    )
    assert resp.status_code == 201
    assert resp.json()["faculty_id"] == info["faculty_id"]


def test_import_duplicate_doi_409(client):
    info = _register_faculty(client)
    payload = _import_payload()
    assert (
        client.post(
            "/api/publications/import-external", headers=_h(info["token"]), json=payload
        ).status_code
        == 201
    )
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(doi=payload["doi"], source_record_id="different-id"),
    )
    assert resp.status_code == 409


def test_import_duplicate_source_record_409(client):
    info = _register_faculty(client)
    src_id = f"PMID-{uuid.uuid4().hex[:8]}"
    payload = _import_payload(
        source="pubmed", source_record_id=src_id, doi=f"10.1111/{uuid.uuid4().hex[:8]}"
    )
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
            source="pubmed", source_record_id=src_id, doi=f"10.2222/{uuid.uuid4().hex[:8]}"
        ),
    )
    assert resp.status_code == 409


def test_import_academic_year_derived(client):
    info = _register_faculty(client)
    ay = mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": "2025-2026"})
    resp = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json=_import_payload(publication_date="2025-08-15"),
    )
    assert resp.status_code == 201
    assert resp.json()["academic_year_id"] == ay["academic_year_id"]


def test_search_does_not_create_records(client, monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(CROSSREF_RESPONSE))
    info = _register_faculty(client)
    before = mongodb.get_collection(PUBLICATIONS).count_documents({})
    client.get(
        "/api/publications/search-external",
        params={"source": "crossref", "query": "x"},
        headers=_h(info["token"]),
    )
    after = mongodb.get_collection(PUBLICATIONS).count_documents({})
    assert before == after
