"""Administrator invitation & admin-registration tests."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.database import mongodb
from app.models.collections import ADMIN_INVITATIONS, USERS
from app.services import admin_invitation_service
from app.utils import security

PASSWORD = "StrongPassword123"
NEW_PASSWORD = "NewAdminPass123"


def _admin_token(client) -> str:
    email = f"inv_admin_{uuid.uuid4().hex[:10]}@example.com"
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


def _faculty(client) -> dict:
    email = f"inv_fac_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Inv Faculty",
            "employee_id": "INV_" + uuid.uuid4().hex[:6],
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


def _create_invitation(client, admin, email=None, expires_in_hours=None):
    body = {"email": email or f"invitee_{uuid.uuid4().hex[:8]}@example.com"}
    if expires_in_hours is not None:
        body["expires_in_hours"] = expires_in_hours
    resp = client.post("/api/admin/invitations", headers=_h(admin), json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register_with_invitation(client, token, email, password=NEW_PASSWORD, name="New Admin"):
    return client.post(
        "/api/auth/admin-register",
        json={"token": token, "email": email, "password": password, "name": name},
    )


# --- Invitation creation & authorization ------------------------------------

def test_admin_can_generate_invitation(client):
    admin = _admin_token(client)
    data = _create_invitation(client, admin)
    assert data["token"]
    assert data["status"] == "pending"
    assert data["email"]
    # Token hash is stored, not the raw token.
    doc = mongodb.get_collection(ADMIN_INVITATIONS).find_one(
        {"invitation_id": data["invitation_id"]}
    )
    assert doc["token_hash"] != data["token"]
    assert len(doc["token_hash"]) == 64  # sha-256 hex


def test_faculty_cannot_generate_or_list_invitations(client):
    info = _faculty(client)
    assert client.post(
        "/api/admin/invitations", headers=_h(info["token"]), json={"email": "x@example.com"}
    ).status_code == 403
    assert client.get("/api/admin/invitations", headers=_h(info["token"])).status_code == 403


def test_unauthenticated_cannot_generate_or_list_invitations(client):
    assert client.post("/api/admin/invitations", json={"email": "x@example.com"}).status_code == 401
    assert client.get("/api/admin/invitations").status_code == 401


def test_invitation_list_hides_tokens(client):
    admin = _admin_token(client)
    _create_invitation(client, admin)
    resp = client.get("/api/admin/invitations", headers=_h(admin))
    assert resp.status_code == 200
    payload = resp.content.decode()
    assert "token_hash" not in payload
    assert '"token"' not in payload  # raw token never listed
    assert resp.json()["total"] >= 1


# --- Successful registration ------------------------------------------------

def test_valid_invitation_registers_admin(client):
    admin = _admin_token(client)
    email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    data = _create_invitation(client, admin, email=email)

    resp = _register_with_invitation(client, data["token"], email)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "admin"
    assert body["email"] == email
    assert "password_hash" not in body

    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["role"] == "admin"
    assert stored["password_hash"].startswith("$2")
    assert stored["password_hash"] != NEW_PASSWORD

    # New admin can sign in and reach admin endpoints.
    login = client.post("/api/auth/login", json={"email": email, "password": NEW_PASSWORD})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get("/api/admin/summary", headers=_h(token)).status_code == 200


def test_invitation_is_single_use(client):
    admin = _admin_token(client)
    email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    data = _create_invitation(client, admin, email=email)

    assert _register_with_invitation(client, data["token"], email).status_code == 201
    second = _register_with_invitation(
        client, data["token"], f"other_{uuid.uuid4().hex[:6]}@example.com"
    )
    assert second.status_code == 400
    assert "already" in second.json()["detail"].lower()


def test_invitation_atomic_consumption(client):
    admin = _admin_token(client)
    email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    data = _create_invitation(client, admin, email=email)
    # First consume succeeds; a direct second consume must fail atomically.
    admin_invitation_service.consume_invitation(data["invitation_id"])
    with pytest.raises(HTTPException) as exc:
        admin_invitation_service.consume_invitation(data["invitation_id"])
    assert exc.value.status_code == 400


# --- Invalid invitation states ----------------------------------------------

def test_missing_invitation_token_rejected(client):
    resp = client.post(
        "/api/auth/admin-register",
        json={"email": f"x_{uuid.uuid4().hex[:6]}@example.com", "password": NEW_PASSWORD},
    )
    assert resp.status_code == 400


def test_invalid_invitation_token_rejected(client):
    resp = _register_with_invitation(
        client, "not-a-real-token-value", f"x_{uuid.uuid4().hex[:6]}@example.com"
    )
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower()


def test_expired_invitation_rejected(client):
    admin = _admin_token(client)
    email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    data = _create_invitation(client, admin, email=email)
    mongodb.get_collection(ADMIN_INVITATIONS).update_one(
        {"invitation_id": data["invitation_id"]},
        {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(hours=1)}},
    )
    resp = _register_with_invitation(client, data["token"], email)
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


def test_revoked_invitation_rejected(client):
    admin = _admin_token(client)
    email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    data = _create_invitation(client, admin, email=email)
    revoke = client.post(
        f"/api/admin/invitations/{data['invitation_id']}/revoke", headers=_h(admin)
    )
    assert revoke.status_code == 200
    resp = _register_with_invitation(client, data["token"], email)
    assert resp.status_code == 400
    assert "revoked" in resp.json()["detail"].lower()


def test_invitation_email_mismatch_rejected(client):
    admin = _admin_token(client)
    data = _create_invitation(client, admin, email="intended@example.com")
    resp = _register_with_invitation(
        client, data["token"], f"different_{uuid.uuid4().hex[:6]}@example.com"
    )
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


def test_duplicate_email_registration_rejected(client):
    admin = _admin_token(client)
    # Existing admin email reused via a fresh invitation.
    existing = _faculty(client)  # existing user (faculty)
    data = _create_invitation(client, admin, email=existing["email"])
    resp = _register_with_invitation(client, data["token"], existing["email"])
    assert resp.status_code == 409
    # Existing account role unchanged.
    stored = mongodb.get_collection(USERS).find_one({"email": existing["email"]})
    assert stored["role"] == "faculty"


# --- Revoke authorization ---------------------------------------------------

def test_only_admin_can_revoke_invitation(client):
    admin = _admin_token(client)
    data = _create_invitation(client, admin)
    info = _faculty(client)
    assert client.post(
        f"/api/admin/invitations/{data['invitation_id']}/revoke",
        headers=_h(info["token"]),
    ).status_code == 403
    assert client.post(
        f"/api/admin/invitations/{data['invitation_id']}/revoke"
    ).status_code == 401


# --- Public faculty registration stays faculty-only -------------------------

def test_public_registration_cannot_become_admin(client):
    email = f"esc_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Escape",
            "role": "admin",
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "faculty"
    assert client.get("/api/admin/summary", headers=_h(
        client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    )).status_code == 403


def test_invitation_cannot_assign_different_role(client):
    # Admin registration ignores any client-supplied role and forces admin.
    admin = _admin_token(client)
    email = f"invitee_{uuid.uuid4().hex[:8]}@example.com"
    data = _create_invitation(client, admin, email=email)
    resp = client.post(
        "/api/auth/admin-register",
        json={
            "token": data["token"],
            "email": email,
            "password": NEW_PASSWORD,
            "role": "faculty",  # ignored
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"
