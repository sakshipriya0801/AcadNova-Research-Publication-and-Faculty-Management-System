"""Faculty-facing academic-year list tests (Step 14F contract fix)."""

import uuid

PASSWORD = "StrongPassword123"


def _register_and_login(client) -> str:
    email = f"aylist_{uuid.uuid4().hex[:10]}@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "name": "Academic Year Faculty", "department_id": "MCA", "designation": "Assistant Professor"},
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return token


def test_academic_years_require_authentication(client):
    resp = client.get("/api/academic-years")
    assert resp.status_code == 401


def test_faculty_can_list_academic_years(client):
    token = _register_and_login(client)
    resp = client.get("/api/academic-years", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    for year in body:
        assert set(year) >= {"academic_year_id", "name", "is_current"}
        assert isinstance(year["is_current"], bool)
        assert "password_hash" not in year
        assert "password" not in year


def test_admin_routes_remain_admin_only(client):
    token = _register_and_login(client)
    resp = client.get(
        "/api/admin/academic-years", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
