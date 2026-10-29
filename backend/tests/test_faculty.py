"""Faculty profile management tests."""

import uuid

import pytest

from app.database import mongodb
from app.models.collections import FACULTY, USERS

PASSWORD = "StrongPassword123"


def _unique_email() -> str:
    return f"faculty_{uuid.uuid4().hex[:10]}@example.com"


def _register_and_login(client, email=None, employee_id=None) -> dict:
    email = email or _unique_email()
    employee_id = employee_id or "EMP_" + uuid.uuid4().hex[:6]
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Original Name",
            "employee_id": employee_id,
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    assert reg.status_code == 201
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {
        "email": email,
        "employee_id": employee_id,
        "token": token,
        "faculty_id": reg.json()["faculty_id"],
    }


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_profile_returns_401(client):
    resp = client.get("/api/faculty/profile")
    assert resp.status_code == 401


def test_view_own_profile(client):
    info = _register_and_login(client)
    resp = client.get("/api/faculty/profile", headers=_headers(info["token"]))

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == info["email"]
    assert body["employee_id"] == info["employee_id"]
    assert body["name"] == "Original Name"
    assert body["faculty_id"] == info["faculty_id"]


def test_update_profile(client):
    info = _register_and_login(client)
    resp = client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"name": "Updated Name", "designation": "Associate Professor"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Name"
    assert body["designation"] == "Associate Professor"


def test_updated_name_saved(client):
    info = _register_and_login(client)
    client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"name": "New Name"},
    )
    doc = mongodb.get_collection(FACULTY).find_one({"faculty_id": info["faculty_id"]})
    assert doc["name"] == "New Name"


def test_updated_designation_saved(client):
    info = _register_and_login(client)
    client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"designation": "Professor"},
    )
    doc = mongodb.get_collection(FACULTY).find_one({"faculty_id": info["faculty_id"]})
    assert doc["designation"] == "Professor"


def test_research_interests_saved(client):
    info = _register_and_login(client)
    resp = client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"research_interests": ["ML", "AI", "ML", "  Data Mining  ", ""]},
    )

    assert resp.status_code == 200
    assert resp.json()["research_interests"] == ["ML", "AI", "Data Mining"]

    doc = mongodb.get_collection(FACULTY).find_one({"faculty_id": info["faculty_id"]})
    assert doc["research_interests"] == ["ML", "AI", "Data Mining"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("orcid_id", "0000-0002-1825-0097"),
        ("scopus_author_id", "57123456789"),
        ("web_of_science_researcher_id", "A-1234-2020"),
        ("pubmed_id", "12345678"),
    ],
)
def test_researcher_identifier_saved(client, field, value):
    info = _register_and_login(client)
    resp = client.put(
        "/api/faculty/profile", headers=_headers(info["token"]), json={field: value}
    )

    assert resp.status_code == 200
    assert resp.json()[field] == value

    doc = mongodb.get_collection(FACULTY).find_one({"faculty_id": info["faculty_id"]})
    assert doc[field] == value


def test_cannot_change_employee_id(client):
    info = _register_and_login(client)
    resp = client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"employee_id": "HACKED", "name": "New Name"},
    )

    assert resp.status_code == 200
    doc = mongodb.get_collection(FACULTY).find_one({"faculty_id": info["faculty_id"]})
    assert doc["employee_id"] == info["employee_id"]
    assert doc["employee_id"] != "HACKED"
    assert doc["name"] == "New Name"


def test_cannot_change_email(client):
    info = _register_and_login(client)
    new_email = _unique_email()
    resp = client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"email": new_email},
    )

    assert resp.status_code == 200
    doc = mongodb.get_collection(FACULTY).find_one({"faculty_id": info["faculty_id"]})
    assert doc["email"] == info["email"]


def test_cannot_change_role(client):
    info = _register_and_login(client)
    resp = client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"role": "admin"},
    )

    assert resp.status_code == 200
    user = mongodb.get_collection(USERS).find_one({"faculty_id": info["faculty_id"]})
    assert user["role"] == "faculty"


def test_password_never_returned(client):
    info = _register_and_login(client)

    get_resp = client.get("/api/faculty/profile", headers=_headers(info["token"]))
    assert "password" not in get_resp.json()
    assert "password_hash" not in get_resp.json()

    put_resp = client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"name": "X"},
    )
    assert "password" not in put_resp.json()
    assert "password_hash" not in put_resp.json()


def test_updated_at_changes_after_update(client):
    info = _register_and_login(client)
    before = mongodb.get_collection(FACULTY).find_one(
        {"faculty_id": info["faculty_id"]}
    )["updated_at"]

    client.put(
        "/api/faculty/profile",
        headers=_headers(info["token"]),
        json={"designation": "Professor"},
    )

    after = mongodb.get_collection(FACULTY).find_one(
        {"faculty_id": info["faculty_id"]}
    )["updated_at"]
    assert after > before
