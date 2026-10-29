"""ORCID integration and author-matching tests (Step 9)."""

import itertools
import uuid

import httpx
import pytest
from fastapi import HTTPException

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, USERS
from app.services import author_matching_service, orcid_service
from app.utils import security
from app.utils.author_matching import normalize_name, normalize_orcid

PASSWORD = "StrongPassword123"

ORCID = "0000-0002-1825-0097"

_orcid_counter = itertools.count(1)


def _unique_orcid() -> str:
    n = next(_orcid_counter)
    return f"{n:04d}-{n:04d}-{n:04d}-{n:03d}X"


ORCID_RECORD = {
    "orcid-identifier": {"path": ORCID, "uri": f"https://orcid.org/{ORCID}"},
    "person": {
        "name": {
            "given-names": {"value": "Sakshi"},
            "family-name": {"value": "Priya"},
            "credit-name": {"value": "Sakshi Priya"},
        },
        "biography": {"content": "Researcher in ML"},
        "emails": {"email": [{"email": "sakshi@example.com"}]},
        "external-identifiers": {
            "external-identifier": [
                {"external-id-type": "Scopus Author ID", "external-id-value": "57123456789"}
            ]
        },
    },
    "activities-summary": {
        "employments": {
            "affiliation-group": [
                {
                    "summaries": [
                        {
                            "organization": {"name": "BV University"},
                            "department-name": "CS",
                            "role-title": "Professor",
                            "start-date": {"year": {"value": "2020"}},
                        }
                    ]
                }
            ]
        }
    },
}

ORCID_WORKS = {
    "group": [
        {
            "work-summary": [
                {
                    "put-code": 123456,
                    "title": {"title": {"value": "My Paper"}},
                    "journal-title": {"value": "Journal X"},
                    "publication-date": {"year": {"value": "2025"}, "month": {"value": "8"}, "day": {"value": "15"}},
                    "external-ids": {"external-id": [{"external-id-type": "doi", "external-id-value": "10.1234/orcidwork"}]},
                    "url": {"value": "https://doi.org/10.1234/orcidwork"},
                }
            ]
        }
    ]
}

ORCID_WORK = {
    "put-code": 123456,
    "title": {"title": {"value": "My Paper"}},
    "journal-title": {"value": "Journal X"},
    "short-description": "Abstract text",
    "publication-date": {"year": {"value": "2025"}, "month": {"value": "8"}, "day": {"value": "15"}},
    "external-ids": {"external-id": [{"external-id-type": "doi", "external-id-value": "10.1234/orcidwork"}]},
    "url": {"value": "https://doi.org/10.1234/orcidwork"},
    "contributors": {
        "contributor": [
            {"credit-name": {"value": "Sakshi Priya"}, "contributor-orcid": {"path": ORCID}},
        ]
    },
}

ORCID_SEARCH = {
    "num-found": 1,
    "result": [
        {
            "orcid-identifier": {"path": ORCID},
            "person": {"name": {"given-names": {"value": "Sakshi"}, "family-name": {"value": "Priya"}}},
        }
    ],
}


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        if self._json is None:
            raise ValueError("invalid json")
        return self._json


def _orcid_handler(url, **kwargs):
    if "/search" in url:
        return _FakeResponse(ORCID_SEARCH)
    if "/work/" in url:
        return _FakeResponse(ORCID_WORK)
    if "/works" in url:
        return _FakeResponse(ORCID_WORKS)
    if "/record" in url:
        return _FakeResponse(ORCID_RECORD)
    raise AssertionError(f"unexpected url: {url}")


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


def _register_faculty(client, orcid=None, name="Sakshi Priya") -> dict:
    email = f"orc_{uuid.uuid4().hex[:10]}@example.com"
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
    if orcid:
        client.put("/api/faculty/profile", headers=_h(token), json={"orcid_id": orcid})
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


# --- ORCID normalization -----------------------------------------------------

def test_normalize_canonical_orcid():
    assert normalize_orcid("0000-0002-1825-0097") == "0000-0002-1825-0097"


def test_normalize_url_orcid():
    assert normalize_orcid("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert normalize_orcid("https://www.orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"


def test_normalize_invalid_orcid():
    assert normalize_orcid("not-an-orcid") is None
    assert normalize_orcid("1234-5678") is None


# --- Author matching ---------------------------------------------------------

def test_orcid_match_high_confidence():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "orcid_id": ORCID},
        {"name": "Sakshi Priya", "orcid_id": ORCID},
    )
    assert result["matched"] is True
    assert result["confidence"] == "high"
    assert "orcid_id" in result["matching_factors"]


def test_different_orcid_no_strong_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "orcid_id": "0000-0001-1111-1111"},
        {"name": "Sakshi Priya", "orcid_id": ORCID},
    )
    assert result["confidence"] != "high"
    assert "orcid_id" not in result["matching_factors"]


def test_exact_name_match():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya"}, {"name": "Sakshi Priya"}
    )
    assert result["matched"] is True
    assert result["confidence"] == "medium"
    assert "exact_name" in result["matching_factors"]


def test_name_case_insensitive():
    assert normalize_name("Sakshi Priya") == normalize_name("sakshi priya")


def test_reversed_name_format():
    assert normalize_name("Priya, Sakshi") == normalize_name("Sakshi Priya")


def test_name_only_match_warns():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya"}, {"name": "Sakshi Priya"}
    )
    assert result["confidence"] == "medium"
    assert any("confirmation" in w for w in result["warnings"])


def test_affiliation_supporting_evidence():
    result = author_matching_service.match_author(
        {"name": "Sakshi Priya", "affiliation": ["BV University"]},
        {"name": "Sakshi Priya"},
    )
    assert "affiliation" in result["matching_factors"]


def test_no_automatic_identity_assignment():
    faculty = {"name": "Sakshi Priya", "orcid_id": None}
    author = {"name": "Sakshi Priya", "orcid_id": ORCID}
    author_matching_service.match_author(author, faculty)
    assert faculty["orcid_id"] is None


# --- ORCID client (mocked) ---------------------------------------------------

def test_orcid_profile(monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    profile = orcid_service.get_researcher(ORCID)
    assert profile.orcid_id == ORCID
    assert profile.given_name == "Sakshi"
    assert profile.family_name == "Priya"


def test_orcid_works(monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    result = orcid_service._client().get_works(ORCID)
    assert result["total"] == 1
    work = result["results"][0]
    assert work.source == "orcid"
    assert work.source_record_id == "123456"
    assert work.title == "My Paper"
    assert work.doi == "10.1234/orcidwork"


def test_orcid_individual_work(monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    work = orcid_service._client().get_work(ORCID, "123456")
    assert work.abstract == "Abstract text"
    assert work.authors[0].name == "Sakshi Priya"
    assert work.authors[0].orcid_id == ORCID


def test_orcid_search(monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    result = orcid_service._client().search_researchers("Sakshi")
    assert result["total"] == 1
    assert result["results"][0].orcid_id == ORCID


def test_orcid_empty_works(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse({"group": []}))
    result = orcid_service._client().get_works(ORCID)
    assert result["total"] == 0


def test_orcid_malformed(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(json_data=None))
    with pytest.raises(HTTPException) as exc:
        orcid_service.get_researcher(ORCID)
    assert exc.value.status_code == 502


def test_orcid_timeout(monkeypatch):
    def raise_timeout(url, **kw):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("httpx.get", raise_timeout)
    with pytest.raises(HTTPException) as exc:
        orcid_service.get_researcher(ORCID)
    assert exc.value.status_code == 504


def test_orcid_http_error(monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, **kw: _FakeResponse(status_code=500))
    with pytest.raises(HTTPException) as exc:
        orcid_service.get_researcher(ORCID)
    assert exc.value.status_code == 502


def test_invalid_orcid_400(monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    with pytest.raises(HTTPException) as exc:
        orcid_service.get_researcher("invalid-orcid")
    assert exc.value.status_code == 400


# --- API ---------------------------------------------------------------------

def test_unauthenticated_orcid_401(client):
    resp = client.get("/api/orcid/profile")
    assert resp.status_code == 401


def test_faculty_orcid_profile(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    info = _register_faculty(client, orcid=_unique_orcid())
    resp = client.get("/api/orcid/profile", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert resp.json()["orcid_id"] == ORCID


def test_admin_orcid_researcher(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    token = _admin_token(client)
    resp = client.get(f"/api/orcid/researcher/{ORCID}", headers=_h(token))
    assert resp.status_code == 200
    assert resp.json()["orcid_id"] == ORCID


def test_missing_faculty_orcid_400(client):
    info = _register_faculty(client)
    resp = client.get("/api/orcid/profile", headers=_h(info["token"]))
    assert resp.status_code == 400


def test_invalid_orcid_api_400(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    token = _admin_token(client)
    resp = client.get("/api/orcid/researcher/not-valid", headers=_h(token))
    assert resp.status_code == 400


def test_orcid_search_api(client, monkeypatch):
    monkeypatch.setattr("httpx.get", _orcid_handler)
    info = _register_faculty(client)
    resp = client.get("/api/orcid/search?query=Sakshi", headers=_h(info["token"]))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# --- Import ------------------------------------------------------------------

def _import_payload(**overrides) -> dict:
    uid = uuid.uuid4().hex[:8]
    payload = {
        "source": "orcid",
        "source_record_id": str(uuid.uuid4().int % 100000),
        "title": "Imported ORCID Paper",
        "authors": [{"name": "Sakshi Priya"}],
        "doi": f"10.1000/{uid}",
        "publication_date": "2025-08-15",
        "journal": "Journal X",
        "indexing": [],
    }
    payload.update(overrides)
    return payload


def test_import_orcid_high_confidence(client):
    orcid = _unique_orcid()
    info = _register_faculty(client, orcid=orcid)
    payload = _import_payload(authors=[{"name": "Sakshi Priya", "orcid_id": orcid}])
    resp = client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "orcid"
    assert body["verification_status"] == "pending"
    assert body["points_awarded"] == 0
    assert body["faculty_id"] == info["faculty_id"]


def test_import_orcid_author_mismatch_400(client):
    faculty_orcid = _unique_orcid()
    info = _register_faculty(client, orcid=faculty_orcid, name="Jane Other")
    payload = _import_payload(
        authors=[{"name": "Sakshi Priya", "orcid_id": _unique_orcid()}]
    )
    resp = client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    )
    assert resp.status_code == 400


def test_import_orcid_confirmed(client):
    faculty_orcid = _unique_orcid()
    info = _register_faculty(client, orcid=faculty_orcid, name="Jane Other")
    payload = _import_payload(
        author_match_confirmed=True,
        authors=[{"name": "Sakshi Priya", "orcid_id": _unique_orcid()}],
    )
    resp = client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    )
    assert resp.status_code == 201


def test_import_orcid_duplicate_doi_409(client):
    orcid = _unique_orcid()
    info = _register_faculty(client, orcid=orcid)
    payload = _import_payload(authors=[{"name": "Sakshi Priya", "orcid_id": orcid}])
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
            doi=payload["doi"],
            source_record_id="99999",
            authors=[{"name": "Sakshi Priya", "orcid_id": orcid}],
        ),
    )
    assert resp.status_code == 409


def test_import_orcid_duplicate_source_record_409(client):
    orcid = _unique_orcid()
    info = _register_faculty(client, orcid=orcid)
    src_id = str(uuid.uuid4().int % 100000)
    authors = [{"name": "Sakshi Priya", "orcid_id": orcid}]
    payload = _import_payload(source_record_id=src_id, authors=authors)
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
            source_record_id=src_id, doi=f"10.2000/{uuid.uuid4().hex[:8]}", authors=authors
        ),
    )
    assert resp.status_code == 409
