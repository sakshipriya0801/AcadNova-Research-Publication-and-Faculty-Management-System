"""Publication-import tests: author matching + academic-year derivation."""

import uuid

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, AUDIT_LOGS, PUBLICATIONS, USERS
from app.services import author_matching_service
from app.utils import security

PASSWORD = "StrongPassword123"


def _ensure_year(name):
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


def _register(client, name="Import Faculty") -> dict:
    email = f"imp_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": name,
            "employee_id": "IMP_" + uuid.uuid4().hex[:6],
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


def _import(client, token, **overrides):
    payload = {
        "source": "crossref",
        "title": "A Publication",
        "authors": [{"name": "Some Author"}],
        "publication_date": "2025-08-15",
    }
    payload.update(overrides)
    return client.post("/api/publications/import-external", headers=_h(token), json=payload)


# --- Author matching (unit) ---------------------------------------------------

def test_matching_email_is_strong():
    result = author_matching_service.match_author(
        {"name": "Jane Doe", "email": "Jane.Doe@Example.com"},
        {"name": "Other Person", "email": "jane.doe@example.com"},
    )
    assert result["confidence"] == "high"
    assert result["result"] == "strong"
    assert "email" in result["matching_factors"]


def test_matching_orcid_is_strong():
    result = author_matching_service.match_author(
        {"name": "Jane Doe", "orcid_id": "https://orcid.org/0000-0002-1825-0097"},
        {"name": "Jane Doe", "orcid_id": "0000-0002-1825-0097"},
    )
    assert result["result"] == "strong"
    assert "orcid_id" in result["matching_factors"]


def test_matching_name_is_uncertain():
    result = author_matching_service.match_author(
        {"name": "Priya, Sakshi."}, {"name": "sakshi priya"}
    )
    assert result["confidence"] == "medium"
    assert result["result"] == "uncertain"
    assert "exact_name" in result["matching_factors"]


def test_matching_no_match():
    result = author_matching_service.match_author(
        {"name": "Totally Different"}, {"name": "Import Faculty"}
    )
    assert result["matched"] is False
    assert result["result"] == "none"
    assert result["matching_factors"] == []


def test_matching_mismatched_identifiers_not_sufficient():
    result = author_matching_service.match_author(
        {"name": "Import Faculty", "scopus_author_id": "111"},
        {"name": "Import Faculty", "scopus_author_id": "222"},
    )
    # Different Scopus IDs are ignored, but the exact name still matches (uncertain).
    assert result["confidence"] == "medium"
    assert "scopus_author_id" not in result["matching_factors"]


def test_matching_empty_metadata():
    result = author_matching_service.match_work_authors({"name": "X"}, [])
    assert result["result"] == "none"
    assert result["matching_factors"] == []


# --- Import: author confirmation ---------------------------------------------

def test_import_requires_confirmation_then_confirm(client):
    _ensure_year("2025-2026")
    info = _register(client, name="Sakshi Priya")
    payload = {
        "source": "scopus",
        "title": "Scopus Work",
        "authors": [{"name": "Someone Else", "scopus_author_id": "999"}],
        "publication_date": "2025-08-15",
    }
    first = client.post("/api/publications/import-external", headers=_h(info["token"]), json=payload)
    assert first.status_code == 400
    assert "author_match_confirmed" in first.json()["detail"]

    second = client.post(
        "/api/publications/import-external",
        headers=_h(info["token"]),
        json={**payload, "author_match_confirmed": True},
    )
    assert second.status_code == 201
    body = second.json()
    assert body["verification_status"] == "pending"

    audit = mongodb.get_collection(AUDIT_LOGS).find_one({"entity_id": body["publication_id"]})
    assert audit is not None
    assert audit["new_value"]["author_match_confirmed"] is True
    assert audit["new_value"]["author_match_result"] == "none"


def test_confirmation_does_not_bypass_duplicate(client):
    _ensure_year("2025-2026")
    info = _register(client)
    payload = {
        "source": "scopus",
        "title": "Dup Work",
        "authors": [{"name": "A Author"}],
        "publication_date": "2025-08-15",
        "source_record_id": "SCOPUS:dup123",
        "author_match_confirmed": True,
    }
    assert client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    ).status_code == 201
    again = client.post(
        "/api/publications/import-external", headers=_h(info["token"]), json=payload
    )
    assert again.status_code == 409


# --- Import: academic year ----------------------------------------------------

def test_import_existing_academic_year(client):
    _ensure_year("2025-2026")
    info = _register(client)
    resp = _import(client, info["token"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["verification_status"] == "pending"
    year = mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": "2025-2026"})
    assert body["academic_year_id"] == year["academic_year_id"]


def test_import_missing_academic_year_rolls_back(client):
    _ensure_year("2025-2026")
    info = _register(client)
    before = mongodb.get_collection(PUBLICATIONS).count_documents({})
    resp = _import(client, info["token"], publication_date="2024-03-01")
    assert resp.status_code == 400
    assert "2023-2024" in resp.json()["detail"]
    # No partial publication is created.
    assert mongodb.get_collection(PUBLICATIONS).count_documents({}) == before


def test_import_historical_date_maps_year(client):
    _ensure_year("2024-2025")
    info = _register(client)
    resp = _import(client, info["token"], publication_date="2025-01-10")
    assert resp.status_code == 201
    year = mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": "2024-2025"})
    assert resp.json()["academic_year_id"] == year["academic_year_id"]


def test_import_year_only_fallback(client):
    _ensure_year("2025-2026")
    info = _register(client)
    resp = _import(
        client, info["token"], publication_date=None, publication_year=2025
    )
    assert resp.status_code == 201
    year = mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": "2025-2026"})
    assert resp.json()["academic_year_id"] == year["academic_year_id"]


def test_import_invalid_date_rejected(client):
    _ensure_year("2025-2026")
    info = _register(client)
    resp = _import(client, info["token"], publication_date=None)
    assert resp.status_code == 400
    assert "publication_date" in resp.json()["detail"]


def test_import_explicit_academic_year_selection(client):
    _ensure_year("2025-2026")
    info = _register(client)
    year = mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": "2025-2026"})
    # Publication date maps to 2024-2025 (missing), but the explicit selection wins.
    resp = _import(
        client,
        info["token"],
        publication_date="2024-11-15",
        academic_year_id=year["academic_year_id"],
    )
    assert resp.status_code == 201
    assert resp.json()["academic_year_id"] == year["academic_year_id"]


def test_import_invalid_academic_year_id_rejected(client):
    _ensure_year("2025-2026")
    info = _register(client)
    resp = _import(
        client,
        info["token"],
        publication_date="2025-08-15",
        academic_year_id="does-not-exist",
    )
    assert resp.status_code == 400
    assert "academic year" in resp.json()["detail"].lower()
