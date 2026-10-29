"""Authentication and user-management tests."""

import uuid

from app.database import mongodb
from app.models.collections import FACULTY, USERS
from app.utils import security

PASSWORD = "StrongPassword123"


def _unique_email(prefix: str = "faculty") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _register(client, email: str, password: str = PASSWORD, employee_id=None):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Test Faculty",
            "employee_id": employee_id,
            "department_id": "MCA",
            "designation": "Assistant Professor",
        },
    )


def _login(client, email: str, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_registration_succeeds(client):
    email = _unique_email()
    resp = _register(client, email, employee_id="EMP_" + uuid.uuid4().hex[:6])

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == "faculty"
    assert body["faculty_id"]
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_rejected(client):
    email = _unique_email()
    assert _register(client, email).status_code == 201
    assert _register(client, email).status_code == 409


def test_duplicate_employee_id_rejected(client):
    employee_id = "EMP_" + uuid.uuid4().hex[:6]
    assert _register(client, _unique_email(), employee_id=employee_id).status_code == 201
    assert _register(client, _unique_email(), employee_id=employee_id).status_code == 409


def test_invalid_registration_input_rejected(client):
    # Missing fields -> 400 (the app maps RequestValidationError to 400).
    assert client.post("/api/auth/register", json={}).status_code == 400
    # Invalid email address.
    assert client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": PASSWORD, "name": "X"},
    ).status_code == 400
    # Weak / short password.
    assert client.post(
        "/api/auth/register",
        json={"email": _unique_email(), "password": "short", "name": "X"},
    ).status_code == 400
    # No user is created for invalid input.
    assert mongodb.get_collection(USERS).count_documents({"email": "not-an-email"}) == 0


def test_password_stored_hashed(client):
    email = _unique_email()
    _register(client, email, password=PASSWORD)

    user = mongodb.get_collection(USERS).find_one({"email": email})
    assert user is not None
    assert user["password_hash"] != PASSWORD
    assert user["password_hash"].startswith("$2")
    assert "password" not in user


def test_login_succeeds(client):
    email = _unique_email()
    _register(client, email)

    resp = _login(client, email)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_login_fails_wrong_password(client):
    email = _unique_email()
    _register(client, email)

    resp = _login(client, email, password="WrongPassword1")
    assert resp.status_code == 401


def test_login_fails_inactive_user(client):
    email = _unique_email()
    _register(client, email)
    mongodb.get_collection(USERS).update_one(
        {"email": email}, {"$set": {"is_active": False}}
    )

    resp = _login(client, email)
    assert resp.status_code == 401


def test_jwt_generated_with_claims(client):
    email = _unique_email()
    _register(client, email)
    token = _login(client, email).json()["access_token"]

    payload = security.decode_access_token(token)
    assert payload["role"] == "faculty"
    assert payload["sub"]
    assert "exp" in payload
    assert "password" not in payload
    assert "password_hash" not in payload


def test_protected_rejects_missing_token(client):
    resp = client.get("/api/auth/test")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate", "").lower() == "bearer"


def test_protected_rejects_invalid_token(client):
    resp = client.get("/api/auth/test", headers=_auth_headers("invalid.token.value"))
    assert resp.status_code == 401


def test_protected_accepts_valid_token(client):
    email = _unique_email()
    _register(client, email)
    token = _login(client, email).json()["access_token"]

    resp = client.get("/api/auth/test", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == {"message": "Authentication successful"}


def test_me_returns_authenticated_user(client):
    email = _unique_email()
    reg = _register(client, email)
    token = _login(client, email).json()["access_token"]

    resp = client.get("/api/auth/me", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == email
    assert body["role"] == "faculty"
    assert body["faculty_id"] == reg.json()["faculty_id"]
    assert "password" not in body
    assert "password_hash" not in body


def test_faculty_cannot_access_admin_endpoint(client):
    email = _unique_email()
    _register(client, email)
    token = _login(client, email).json()["access_token"]

    resp = client.get("/api/auth/admin-test", headers=_auth_headers(token))
    assert resp.status_code == 403


def test_admin_can_access_admin_endpoint(client):
    email = "admin_" + uuid.uuid4().hex[:10] + "@example.com"
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
    token = _login(client, email).json()["access_token"]

    resp = client.get("/api/auth/admin-test", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == {"message": "Admin access granted"}


# --- Administrator login & database-outage handling -------------------------

def test_admin_login_success(client):
    email = f"admin_{uuid.uuid4().hex[:10]}@example.com"
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
    resp = _login(client, email)
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get("/api/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_login_nonexistent_account_401(client):
    resp = _login(client, f"ghost_{uuid.uuid4().hex[:8]}@example.com")
    assert resp.status_code == 401
    assert "password" in resp.json()["detail"].lower()


def test_login_database_unavailable_returns_503(client, monkeypatch):
    from pymongo.errors import ServerSelectionTimeoutError

    from app.services import user_service

    def _boom(email):
        raise ServerSelectionTimeoutError("database unreachable")

    monkeypatch.setattr(user_service, "find_user_by_email", _boom)
    resp = _login(client, f"x_{uuid.uuid4().hex[:6]}@example.com")
    assert resp.status_code == 503
    assert "database" in resp.json()["detail"].lower()


# --- Common faculty-profile fields (department + designation) ---------------

def test_registration_requires_department_and_designation(client):
    email = _unique_email()
    missing = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "name": "X"},
    )
    assert missing.status_code == 400

    invalid_dept = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "X",
            "department_id": "Engineering",
            "designation": "Assistant Professor",
        },
    )
    assert invalid_dept.status_code == 400

    invalid_desig = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "X",
            "department_id": "MCA",
            "designation": "Dean",
        },
    )
    assert invalid_desig.status_code == 400


def test_registration_persists_department_and_designation(client):
    email = _unique_email()
    resp = _register(client, email)
    assert resp.status_code == 201
    faculty = mongodb.get_collection(FACULTY).find_one({"email": email})
    assert faculty["department_id"] == "MCA"
    assert faculty["designation"] == "Assistant Professor"
