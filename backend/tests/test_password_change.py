"""Mandatory first-login password-change tests."""

import json
import uuid

from app.database import mongodb
from app.models.collections import USERS
from app.utils import security

PASSWORD = "StrongPassword123"
TEMP_PASSWORD = "TempPass123"
NEW_PASSWORD = "NewPass123"


def _admin_token(client) -> str:
    email = f"pc_admin_{uuid.uuid4().hex[:10]}@example.com"
    mongodb.get_collection(USERS).insert_one(
        {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "password_hash": security.hash_password(PASSWORD),
            "role": "admin",
            "faculty_id": None,
            "is_active": True,
            "approval_status": "approved",
            "must_change_password": False,
        }
    )
    return client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_faculty(client, admin, email, password=None):
    body = {
        "name": "Faculty One",
        "email": email,
        "department_id": "MCA",
        "designation": "Professor",
    }
    if password is not None:
        body["password"] = password
    resp = client.post("/api/admin/faculty", headers=_h(admin), json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# --- Flags ----------------------------------------------------------------

def test_admin_created_faculty_has_flag(client):
    admin = _admin_token(client)
    email = f"flag_{uuid.uuid4().hex[:8]}@example.com"
    _create_faculty(client, admin, email, password=TEMP_PASSWORD)

    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["must_change_password"] is True

    login = _login(client, email, TEMP_PASSWORD)
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True

    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers=_h(token))
    assert me.json()["must_change_password"] is True


def test_self_registered_faculty_not_forced(client):
    email = f"self_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Self Faculty",
            "employee_id": "PC_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    assert reg.status_code == 201

    login = _login(client, email, PASSWORD)
    assert login.status_code == 200
    assert login.json()["must_change_password"] is False


def test_admin_not_forced(client):
    admin = _admin_token(client)
    assert client.get("/api/admin/summary", headers=_h(admin)).status_code == 200


# --- Enforcement ----------------------------------------------------------

def test_faculty_blocked_before_change(client):
    admin = _admin_token(client)
    email = f"blocked_{uuid.uuid4().hex[:8]}@example.com"
    _create_faculty(client, admin, email, password=TEMP_PASSWORD)

    token = _login(client, email, TEMP_PASSWORD).json()["access_token"]
    # Minimum endpoint is reachable.
    assert client.get("/api/auth/me", headers=_h(token)).status_code == 200
    # Protected faculty endpoints are denied with a clear message.
    denied = client.get("/api/publications", headers=_h(token))
    assert denied.status_code == 403
    assert "password" in denied.json()["detail"].lower()


# --- Successful change ----------------------------------------------------

def test_change_password_success(client):
    admin = _admin_token(client)
    email = f"change_{uuid.uuid4().hex[:8]}@example.com"
    _create_faculty(client, admin, email, password=TEMP_PASSWORD)
    token = _login(client, email, TEMP_PASSWORD).json()["access_token"]

    resp = client.post(
        "/api/auth/change-password",
        headers=_h(token),
        json={"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["must_change_password"] is False
    assert "password_hash" not in body
    assert "generated_password" not in body

    # Old temporary password no longer works.
    assert _login(client, email, TEMP_PASSWORD).status_code == 401
    # New password works and grants full access.
    new_token = _login(client, email, NEW_PASSWORD).json()["access_token"]
    assert client.get("/api/publications", headers=_h(new_token)).status_code == 200

    # Stored password is a fresh bcrypt hash, not plaintext.
    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["password_hash"].startswith("$2")
    assert stored["password_hash"] != NEW_PASSWORD
    assert stored["must_change_password"] is False


# --- Validation -----------------------------------------------------------

def test_mismatched_passwords_rejected(client):
    admin = _admin_token(client)
    email = f"mismatch_{uuid.uuid4().hex[:8]}@example.com"
    _create_faculty(client, admin, email, password=TEMP_PASSWORD)
    token = _login(client, email, TEMP_PASSWORD).json()["access_token"]
    resp = client.post(
        "/api/auth/change-password",
        headers=_h(token),
        json={"new_password": NEW_PASSWORD, "confirm_password": "Different123"},
    )
    assert resp.status_code == 400


def test_weak_new_password_rejected(client):
    admin = _admin_token(client)
    email = f"weak_{uuid.uuid4().hex[:8]}@example.com"
    _create_faculty(client, admin, email, password=TEMP_PASSWORD)
    token = _login(client, email, TEMP_PASSWORD).json()["access_token"]
    resp = client.post(
        "/api/auth/change-password",
        headers=_h(token),
        json={"new_password": "short", "confirm_password": "short"},
    )
    assert resp.status_code == 400


def test_new_password_must_differ_from_temp(client):
    admin = _admin_token(client)
    email = f"same_{uuid.uuid4().hex[:8]}@example.com"
    _create_faculty(client, admin, email, password=TEMP_PASSWORD)
    token = _login(client, email, TEMP_PASSWORD).json()["access_token"]
    resp = client.post(
        "/api/auth/change-password",
        headers=_h(token),
        json={"new_password": TEMP_PASSWORD, "confirm_password": TEMP_PASSWORD},
    )
    assert resp.status_code == 400


def test_unauthenticated_cannot_change_password(client):
    resp = client.post(
        "/api/auth/change-password",
        json={"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
    )
    assert resp.status_code == 401
