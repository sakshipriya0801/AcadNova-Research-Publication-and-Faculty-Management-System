"""Publication management tests."""

import uuid

import pytest

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, PUBLICATIONS

PASSWORD = "StrongPassword123"


def _unique_email(prefix: str = "pub") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _seed_academic_years():
    db = mongodb.get_database()
    for name, start_year in [
        ("2024-2025", 2024),
        ("2025-2026", 2025),
        ("2026-2027", 2026),
    ]:
        if db[ACADEMIC_YEARS].find_one({"name": name}) is None:
            db[ACADEMIC_YEARS].insert_one(
                {
                    "academic_year_id": str(uuid.uuid4()),
                    "name": name,
                    "start_date": f"{start_year}-07-01",
                    "end_date": f"{start_year + 1}-06-30",
                    "is_current": False,
                }
            )


@pytest.fixture(autouse=True)
def _academic_years(client):
    _seed_academic_years()
    yield


def _register_and_login(client) -> dict:
    email = _unique_email()
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Pub Faculty",
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
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
    }


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _base_payload(**overrides) -> dict:
    payload = {
        "title": "A Study of Machine Learning",
        "authors": ["Author One", "Author Two"],
        "publication_type": "research_publication",
        "faculty_author_position": 1,
        "publication_date": "2025-08-15",
        "journal_name": "Journal of AI",
    }
    payload.update(overrides)
    return payload


def _create(client, token, **overrides):
    return client.post(
        "/api/publications", headers=_headers(token), json=_base_payload(**overrides)
    )


def test_unauthenticated_create_returns_401(client):
    resp = client.post("/api/publications", json=_base_payload())
    assert resp.status_code == 401


def test_create_publication(client):
    info = _register_and_login(client)
    resp = _create(client, info["token"])

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "A Study of Machine Learning"
    assert body["authors"] == ["Author One", "Author Two"]
    assert body["author_count"] == 2
    assert body["faculty_id"] == info["faculty_id"]


def test_faculty_id_comes_from_auth(client):
    info = _register_and_login(client)
    resp = _create(client, info["token"], faculty_id="HACKED")

    assert resp.status_code == 201
    doc = mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": resp.json()["publication_id"]}
    )
    assert doc["faculty_id"] == info["faculty_id"]
    assert doc["faculty_id"] != "HACKED"


def test_points_awarded_starts_at_zero(client):
    info = _register_and_login(client)
    resp = _create(client, info["token"])

    assert resp.json()["points_awarded"] == 0
    doc = mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": resp.json()["publication_id"]}
    )
    assert doc["points_awarded"] == 0


def test_verification_status_starts_pending(client):
    info = _register_and_login(client)
    resp = _create(client, info["token"])
    assert resp.json()["verification_status"] == "pending"


def test_publication_year_derived_from_date(client):
    info = _register_and_login(client)
    resp = _create(
        client, info["token"], publication_date="2025-08-15", publication_year=1999
    )
    assert resp.json()["publication_year"] == 2025


def test_academic_year_assigned(client):
    info = _register_and_login(client)
    resp = _create(client, info["token"], publication_date="2025-08-15")

    doc = mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": resp.json()["publication_id"]}
    )
    academic_year = mongodb.get_collection(ACADEMIC_YEARS).find_one(
        {"name": "2025-2026"}
    )
    assert doc["academic_year_id"] == academic_year["academic_year_id"]


def test_empty_authors_rejected(client):
    info = _register_and_login(client)
    resp = _create(client, info["token"], authors=[])
    assert resp.status_code == 400


def test_invalid_author_position_rejected(client):
    info = _register_and_login(client)
    resp = _create(
        client, info["token"], authors=["A", "B", "C"], faculty_author_position=5
    )
    assert resp.status_code == 400


def test_doi_normalized(client):
    info = _register_and_login(client)
    doi = f"10.1234/{uuid.uuid4().hex[:8].upper()}"
    resp = _create(client, info["token"], doi=f"https://doi.org/{doi}")
    assert resp.json()["doi"] == doi.lower()


def test_duplicate_doi_rejected(client):
    info = _register_and_login(client)
    doi = f"10.1234/{uuid.uuid4().hex[:8].upper()}"
    assert _create(client, info["token"], doi=doi.lower()).status_code == 201
    resp = _create(client, info["token"], doi=f"https://doi.org/{doi}")
    assert resp.status_code == 409


def test_list_own_publications(client):
    info = _register_and_login(client)
    _create(client, info["token"], title="First Paper")
    _create(client, info["token"], title="Second Paper")

    resp = client.get("/api/publications", headers=_headers(info["token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(item["faculty_id"] == info["faculty_id"] for item in body["items"])


def test_pagination(client):
    info = _register_and_login(client)
    for i in range(3):
        _create(client, info["token"], title=f"Paper {i}")

    resp = client.get(
        "/api/publications?page=1&page_size=2", headers=_headers(info["token"])
    )
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 3
    assert body["total_pages"] == 2


def test_search(client):
    info = _register_and_login(client)
    _create(client, info["token"], title="Machine Learning in Education")

    resp = client.get(
        "/api/publications?search=machine", headers=_headers(info["token"])
    )
    assert resp.json()["total"] == 1

    resp = client.get(
        "/api/publications?search=zzzznothing", headers=_headers(info["token"])
    )
    assert resp.json()["total"] == 0


def test_filter_publication_type(client):
    info = _register_and_login(client)
    _create(client, info["token"], title="Paper A", publication_type="research_publication")
    _create(client, info["token"], title="Paper B", publication_type="book_chapter")

    resp = client.get(
        "/api/publications?publication_type=research_publication",
        headers=_headers(info["token"]),
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["publication_type"] == "research_publication"


def test_filter_publication_year(client):
    info = _register_and_login(client)
    _create(client, info["token"], title="Paper 2025", publication_date="2025-08-15")
    _create(client, info["token"], title="Paper 2024", publication_date="2024-08-15")

    resp = client.get(
        "/api/publications?publication_year=2025", headers=_headers(info["token"])
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["publication_year"] == 2025


def test_filter_source(client):
    info = _register_and_login(client)
    _create(client, info["token"], title="Manual Paper")

    resp = client.get(
        "/api/publications?source=manual", headers=_headers(info["token"])
    )
    assert resp.json()["total"] == 1

    resp = client.get(
        "/api/publications?source=scopus", headers=_headers(info["token"])
    )
    assert resp.json()["total"] == 0


def test_get_own_publication(client):
    info = _register_and_login(client)
    created = _create(client, info["token"], title="My Paper").json()

    resp = client.get(
        f"/api/publications/{created['publication_id']}", headers=_headers(info["token"])
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Paper"


def test_cannot_access_other_faculty_publication(client):
    info_a = _register_and_login(client)
    info_b = _register_and_login(client)
    created = _create(client, info_a["token"], title="A's Paper").json()

    resp = client.get(
        f"/api/publications/{created['publication_id']}", headers=_headers(info_b["token"])
    )
    assert resp.status_code == 404


def test_update_own_publication(client):
    info = _register_and_login(client)
    created = _create(client, info["token"], title="Old Title").json()

    resp = client.put(
        f"/api/publications/{created['publication_id']}",
        headers=_headers(info["token"]),
        json={"title": "New Title", "abstract": "Updated abstract"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["abstract"] == "Updated abstract"


def test_protected_fields_cannot_be_changed(client):
    info = _register_and_login(client)
    created = _create(client, info["token"]).json()

    resp = client.put(
        f"/api/publications/{created['publication_id']}",
        headers=_headers(info["token"]),
        json={
            "points_awarded": 999,
            "verification_status": "verified",
            "faculty_id": "HACKED",
            "source": "scopus",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["points_awarded"] == 0
    assert body["verification_status"] == "pending"
    assert body["faculty_id"] == info["faculty_id"]
    assert body["source"] == "manual"


def test_change_date_updates_academic_year(client):
    info = _register_and_login(client)
    created = _create(client, info["token"], publication_date="2025-08-15").json()

    resp = client.put(
        f"/api/publications/{created['publication_id']}",
        headers=_headers(info["token"]),
        json={"publication_date": "2026-08-15"},
    )
    assert resp.status_code == 200
    assert resp.json()["publication_year"] == 2026

    ay_2026 = mongodb.get_collection(ACADEMIC_YEARS).find_one({"name": "2026-2027"})
    assert resp.json()["academic_year_id"] == ay_2026["academic_year_id"]


def test_change_doi_duplicate_validation(client):
    info = _register_and_login(client)
    doi_a = f"10.1111/{uuid.uuid4().hex[:8]}"
    doi_b = f"10.2222/{uuid.uuid4().hex[:8]}"
    pub_a = _create(client, info["token"], title="A", doi=doi_a).json()
    pub_b = _create(client, info["token"], title="B", doi=doi_b).json()

    resp = client.put(
        f"/api/publications/{pub_b['publication_id']}",
        headers=_headers(info["token"]),
        json={"doi": doi_a},
    )
    assert resp.status_code == 409


def test_delete_own_publication(client):
    info = _register_and_login(client)
    created = _create(client, info["token"], title="To Delete").json()

    resp = client.delete(
        f"/api/publications/{created['publication_id']}", headers=_headers(info["token"])
    )
    assert resp.status_code == 204

    get_resp = client.get(
        f"/api/publications/{created['publication_id']}", headers=_headers(info["token"])
    )
    assert get_resp.status_code == 404


def test_cannot_delete_other_faculty_publication(client):
    info_a = _register_and_login(client)
    info_b = _register_and_login(client)
    created = _create(client, info_a["token"], title="A's Paper").json()

    resp = client.delete(
        f"/api/publications/{created['publication_id']}", headers=_headers(info_b["token"])
    )
    assert resp.status_code == 404

    still_there = mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": created["publication_id"]}
    )
    assert still_there is not None
