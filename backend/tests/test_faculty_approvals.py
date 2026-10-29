"""Faculty registration approval workflow tests.

These tests explicitly enable the registration-approval requirement (the shared
conftest disables it so legacy register-then-login flows remain green).
"""

import json
import uuid

import pytest

from app.config.settings import get_settings
from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, USERS
from app.utils import security

PASSWORD = "StrongPassword123"
TEMP_PASSWORD = "TempPass123"


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


@pytest.fixture(autouse=True)
def _require_approval(monkeypatch):
    monkeypatch.setenv("REQUIRE_REGISTRATION_APPROVAL", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _admin_token(client) -> str:
    email = f"approv_admin_{uuid.uuid4().hex[:10]}@example.com"
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


def _register(client, email, password=PASSWORD, **extra):
    body = {
        "email": email,
        "password": password,
        "name": "Approval Faculty",
        "employee_id": "APR_" + uuid.uuid4().hex[:6],
        "department_id": "MCA",
        "designation": "Assistant Professor",
    }
    body.update(extra)
    return client.post("/api/auth/register", json=body)


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# --- Self-registration is pending and blocked -------------------------------

def test_self_registration_is_pending(client):
    email = f"pending_{uuid.uuid4().hex[:8]}@example.com"
    resp = _register(client, email)
    assert resp.status_code == 201
    assert resp.json()["approval_status"] == "pending"
    assert resp.json()["role"] == "faculty"

    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["approval_status"] == "pending"

    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 403
    assert "pending" in login.json()["detail"].lower()


def test_pending_faculty_cannot_access_protected_endpoint(client):
    email = f"pending2_{uuid.uuid4().hex[:8]}@example.com"
    _register(client, email)
    # No token can be obtained, so even a forged call is blocked server-side.
    assert client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).status_code == 403


# --- Approval ---------------------------------------------------------------

def test_admin_approve_allows_login_and_publications(client):
    _ensure_year()
    admin = _admin_token(client)
    email = f"approve_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(client, email)
    faculty_id = reg.json()["faculty_id"]

    approve = client.post(f"/api/admin/faculty/{faculty_id}/approve", headers=_h(admin))
    assert approve.status_code == 200
    assert approve.json()["approval_status"] == "approved"

    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get("/api/auth/me", headers=_h(token)).status_code == 200

    pub = client.post(
        "/api/publications",
        headers=_h(token),
        json={
            "title": "Approved Faculty Publication",
            "authors": ["Approval Faculty"],
            "publication_type": "research_publication",
            "faculty_author_position": 1,
            "publication_date": "2025-08-15",
            "indexing": ["Scopus"],
        },
    )
    assert pub.status_code == 201


def test_admin_reject_with_reason(client):
    admin = _admin_token(client)
    email = f"reject_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(client, email)
    faculty_id = reg.json()["faculty_id"]

    reject = client.post(
        f"/api/admin/faculty/{faculty_id}/reject",
        headers=_h(admin),
        json={"reason": "Invalid employee record"},
    )
    assert reject.status_code == 200
    assert reject.json()["approval_status"] == "rejected"
    assert reject.json()["rejection_reason"] == "Invalid employee record"

    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 403
    assert "rejected" in login.json()["detail"].lower()

    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["rejection_reason"] == "Invalid employee record"


def test_approve_is_idempotent(client):
    admin = _admin_token(client)
    email = f"idem_{uuid.uuid4().hex[:8]}@example.com"
    faculty_id = _register(client, email).json()["faculty_id"]
    assert client.post(
        f"/api/admin/faculty/{faculty_id}/approve", headers=_h(admin)
    ).status_code == 200
    assert client.post(
        f"/api/admin/faculty/{faculty_id}/approve", headers=_h(admin)
    ).status_code == 200


# --- Listing & authorization ------------------------------------------------

def test_admin_can_list_pending_applications(client):
    admin = _admin_token(client)
    _register(client, f"list1_{uuid.uuid4().hex[:8]}@example.com")
    _register(client, f"list2_{uuid.uuid4().hex[:8]}@example.com")
    resp = client.get("/api/admin/faculty/approvals", headers=_h(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert all(item["approval_status"] == "pending" for item in body["items"])


def test_faculty_and_anonymous_cannot_manage_approvals(client):
    admin = _admin_token(client)
    email = f"authz_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(client, email)
    faculty_id = reg.json()["faculty_id"]
    client.post(f"/api/admin/faculty/{faculty_id}/approve", headers=_h(admin))

    faculty_token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]

    assert client.get(
        "/api/admin/faculty/approvals", headers=_h(faculty_token)
    ).status_code == 403
    assert client.post(
        f"/api/admin/faculty/{faculty_id}/approve", headers=_h(faculty_token)
    ).status_code == 403
    assert client.get("/api/admin/faculty/approvals").status_code == 401


# --- Admin-created faculty (Method A) ---------------------------------------

def test_admin_can_create_faculty_account(client):
    admin = _admin_token(client)
    email = f"created_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/admin/faculty",
        headers=_h(admin),
        json={
            "name": "Created Faculty",
            "email": email,
            "password": TEMP_PASSWORD,
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "password_hash" not in body
    # Explicit password was supplied -> it must NOT be returned again.
    assert body.get("generated_password") is None

    login = client.post("/api/auth/login", json={"email": email, "password": TEMP_PASSWORD})
    assert login.status_code == 200
    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["role"] == "faculty"
    assert stored["approval_status"] == "approved"
    assert stored["password_hash"].startswith("$2")


def test_admin_create_faculty_duplicate_and_invalid(client):
    admin = _admin_token(client)
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Dup Faculty",
        "email": email,
        "password": TEMP_PASSWORD,
        "department_id": "MBA",
        "designation": "Professor",
    }
    assert client.post("/api/admin/faculty", headers=_h(admin), json=payload).status_code == 201
    assert client.post("/api/admin/faculty", headers=_h(admin), json=payload).status_code == 409
    # weak password -> 400
    assert client.post(
        "/api/admin/faculty",
        headers=_h(admin),
        json={
            "name": "X",
            "email": f"weak_{uuid.uuid4().hex[:6]}@example.com",
            "password": "short",
            "department_id": "BCA",
            "designation": "Lecturer",
        },
    ).status_code == 400


def test_admin_create_faculty_requires_valid_department_and_designation(client):
    admin = _admin_token(client)

    def body(**overrides):
        base = {
            "name": "Validated Faculty",
            "email": f"val_{uuid.uuid4().hex[:6]}@example.com",
            "department_id": "MCA",
            "designation": "Professor",
        }
        base.update(overrides)
        return base

    # Valid combination.
    assert client.post(
        "/api/admin/faculty", headers=_h(admin), json=body()
    ).status_code == 201

    # Invalid department.
    assert client.post(
        "/api/admin/faculty", headers=_h(admin), json=body(department_id="Engineering")
    ).status_code == 400
    # Invalid designation.
    assert client.post(
        "/api/admin/faculty", headers=_h(admin), json=body(designation="Dean")
    ).status_code == 400
    # Missing required department/designation.
    missing = body()
    missing.pop("department_id")
    assert client.post(
        "/api/admin/faculty", headers=_h(admin), json=missing
    ).status_code == 400


def test_blank_password_generates_secure_temp_password(client):
    admin = _admin_token(client)
    email = f"gen_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/admin/faculty",
        headers=_h(admin),
        json={
            "name": "Generated Password Faculty",
            "email": email,
            "department_id": "BBA",
            "designation": "Visiting Faculty",
        },
    )
    assert resp.status_code == 201, resp.text
    generated = resp.json()["generated_password"]
    assert isinstance(generated, str) and len(generated) == 5
    assert generated.isalnum()
    assert any(c.isalpha() for c in generated) and any(c.isdigit() for c in generated)

    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["password_hash"].startswith("$2")
    assert stored["password_hash"] != generated  # hashed, not plaintext

    login = client.post("/api/auth/login", json={"email": email, "password": generated})
    assert login.status_code == 200

    # The generated password is NOT exposed in the faculty list response.
    listed = client.get("/api/admin/faculty", headers=_h(admin)).content.decode()
    assert generated not in listed
    assert "generated_password" not in listed


def test_public_registration_cannot_set_role_or_approval(client):
    email = f"esc2_{uuid.uuid4().hex[:8]}@example.com"
    resp = _register(
        client,
        email,
        role="admin",
        approval_status="approved",
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "faculty"
    assert resp.json()["approval_status"] == "pending"
    assert client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).status_code == 403


def test_legacy_faculty_without_approval_status_can_login(client):
    email = f"legacy_{uuid.uuid4().hex[:8]}@example.com"
    mongodb.get_collection(USERS).insert_one(
        {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password_hash": security.hash_password(PASSWORD),
            "role": "faculty",
            "faculty_id": None,
            "is_active": True,
            # no approval_status -> treated as approved (reconciliation)
        }
    )
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
