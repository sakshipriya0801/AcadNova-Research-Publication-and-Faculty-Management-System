"""Faculty-facing department list tests (Step 14G contract fix)."""

import uuid

PASSWORD = "StrongPassword123"


def _register_and_login(client) -> str:
    email = f"deptlist_{uuid.uuid4().hex[:10]}@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "name": "Department Faculty", "department_id": "MCA", "designation": "Assistant Professor"},
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return token


def test_departments_require_authentication(client):
    resp = client.get("/api/departments")
    assert resp.status_code == 401


def test_faculty_can_list_departments(client):
    token = _register_and_login(client)
    resp = client.get("/api/departments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    for department in body:
        assert set(department) >= {"department_id", "name"}
        assert isinstance(department["name"], str) and department["name"]
        assert "password_hash" not in department
        assert "password" not in department


def test_admin_department_management_remains_admin_only(client):
    token = _register_and_login(client)
    resp = client.get(
        "/api/admin/departments", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
