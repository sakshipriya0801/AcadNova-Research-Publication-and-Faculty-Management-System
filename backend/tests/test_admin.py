"""Admin management tests (Step 7)."""

import itertools
import json
import uuid

import pytest

from app.database import mongodb
from app.models.collections import PUBLICATIONS, USERS
from app.utils import security
from scripts.seed_rules import seed_eligibility_rules, seed_publication_rules

PASSWORD = "StrongPassword123"

_year_counter = itertools.count(2090)


def _year_payload() -> dict:
    y = next(_year_counter)
    return {
        "name": f"{y}-{y + 1}",
        "start_date": f"{y}-07-01",
        "end_date": f"{y + 1}-06-30",
    }


def _code() -> str:
    return "CODE-" + uuid.uuid4().hex[:8]


def _rule_code() -> str:
    return "RULE-" + uuid.uuid4().hex[:8]


@pytest.fixture(autouse=True)
def _seed(client):
    seed_publication_rules()
    seed_eligibility_rules()
    yield


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


def _register_faculty(client, designation="Assistant Professor", name="Test Faculty") -> dict:
    email = f"fac_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": name,
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": designation,
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"email": email, "token": token, "faculty_id": reg.json()["faculty_id"]}


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# --- Security ---------------------------------------------------------------

def test_faculty_gets_403_on_admin_endpoint(client):
    info = _register_faculty(client)
    resp = client.get("/api/admin/faculty", headers=_h(info["token"]))
    assert resp.status_code == 403


def test_unauthenticated_gets_401(client):
    resp = client.get("/api/admin/faculty")
    assert resp.status_code == 401


def test_admin_gets_success(client):
    token = _admin_token(client)
    resp = client.get("/api/admin/faculty", headers=_h(token))
    assert resp.status_code == 200


# --- Academic years ---------------------------------------------------------

def test_faculty_cannot_create_academic_year(client):
    info = _register_faculty(client)
    resp = client.post(
        "/api/admin/academic-years", headers=_h(info["token"]), json=_year_payload()
    )
    assert resp.status_code == 403


def test_admin_can_create_academic_year(client):
    token = _admin_token(client)
    payload = _year_payload()
    resp = client.post("/api/admin/academic-years", headers=_h(token), json=payload)
    assert resp.status_code == 201
    assert resp.json()["name"] == payload["name"]


def test_duplicate_academic_year_rejected(client):
    token = _admin_token(client)
    payload = _year_payload()
    assert client.post("/api/admin/academic-years", headers=_h(token), json=payload).status_code == 201
    resp = client.post("/api/admin/academic-years", headers=_h(token), json=payload)
    assert resp.status_code == 409


def test_invalid_date_range_rejected(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/academic-years",
        headers=_h(token),
        json={"name": "2026-2027", "start_date": "2027-06-30", "end_date": "2026-07-01"},
    )
    assert resp.status_code == 400


def test_invalid_july_june_rejected(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/academic-years",
        headers=_h(token),
        json={"name": "2026-2027", "start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    assert resp.status_code == 400


def test_admin_can_list_academic_years(client):
    token = _admin_token(client)
    payload = _year_payload()
    client.post("/api/admin/academic-years", headers=_h(token), json=payload)
    resp = client.get("/api/admin/academic-years", headers=_h(token))
    assert resp.status_code == 200
    assert any(y["name"] == payload["name"] for y in resp.json())


def test_admin_can_update_academic_year(client):
    token = _admin_token(client)
    payload = _year_payload()
    created = client.post("/api/admin/academic-years", headers=_h(token), json=payload).json()
    resp = client.put(
        f"/api/admin/academic-years/{created['academic_year_id']}",
        headers=_h(token),
        json=payload,
    )
    assert resp.status_code == 200


def test_only_one_academic_year_current(client):
    token = _admin_token(client)
    year1 = client.post("/api/admin/academic-years", headers=_h(token), json=_year_payload()).json()
    year2 = client.post("/api/admin/academic-years", headers=_h(token), json=_year_payload()).json()

    client.patch(f"/api/admin/academic-years/{year1['academic_year_id']}/current", headers=_h(token))
    client.patch(f"/api/admin/academic-years/{year2['academic_year_id']}/current", headers=_h(token))

    years = client.get("/api/admin/academic-years", headers=_h(token)).json()
    current = [y for y in years if y["is_current"]]
    assert len(current) == 1
    assert current[0]["academic_year_id"] == year2["academic_year_id"]


def test_academic_year_with_publications_cannot_delete(client):
    token = _admin_token(client)
    year = client.post("/api/admin/academic-years", headers=_h(token), json=_year_payload()).json()

    mongodb.get_collection(PUBLICATIONS).insert_one(
        {
            "publication_id": str(uuid.uuid4()),
            "title": "Dep",
            "faculty_id": "x",
            "academic_year_id": year["academic_year_id"],
            "verification_status": "pending",
        }
    )

    resp = client.delete(
        f"/api/admin/academic-years/{year['academic_year_id']}", headers=_h(token)
    )
    assert resp.status_code == 409


# --- Departments ------------------------------------------------------------

def test_admin_can_create_department(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/departments",
        headers=_h(token),
        json={"name": "Computer Science", "code": _code()},
    )
    assert resp.status_code == 201


def test_duplicate_department_code_rejected(client):
    token = _admin_token(client)
    code = _code()
    payload = {"name": "Computer Science", "code": code}
    assert client.post("/api/admin/departments", headers=_h(token), json=payload).status_code == 201
    resp = client.post("/api/admin/departments", headers=_h(token), json=payload)
    assert resp.status_code == 409


def test_admin_can_update_department(client):
    token = _admin_token(client)
    created = client.post(
        "/api/admin/departments", headers=_h(token), json={"name": "CS", "code": _code()}
    ).json()
    resp = client.put(
        f"/api/admin/departments/{created['department_id']}",
        headers=_h(token),
        json={"name": "Computer Science"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Computer Science"


def test_department_used_by_faculty_cannot_delete(client):
    token = _admin_token(client)
    dept = client.post(
        "/api/admin/departments", headers=_h(token), json={"name": "CS", "code": _code()}
    ).json()
    _register_faculty(client)
    facs = client.get("/api/admin/faculty", headers=_h(token)).json()
    fac_id = facs["items"][0]["faculty_id"]
    client.put(
        f"/api/admin/faculty/{fac_id}",
        headers=_h(token),
        json={"department_id": dept["department_id"]},
    )

    resp = client.delete(f"/api/admin/departments/{dept['department_id']}", headers=_h(token))
    assert resp.status_code == 409


def test_admin_can_deactivate_department(client):
    token = _admin_token(client)
    dept = client.post(
        "/api/admin/departments", headers=_h(token), json={"name": "CS", "code": _code()}
    ).json()
    resp = client.patch(
        f"/api/admin/departments/{dept['department_id']}/deactivate", headers=_h(token)
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# --- Faculty -----------------------------------------------------------------

def test_admin_can_list_faculty(client):
    token = _admin_token(client)
    _register_faculty(client, name="Alice Smith")
    resp = client.get("/api/admin/faculty", headers=_h(token))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_admin_can_search_faculty(client):
    token = _admin_token(client)
    marker = uuid.uuid4().hex[:10]
    _register_faculty(client, name=f"Alice {marker}")
    _register_faculty(client, name="Bob Other")
    resp = client.get(f"/api/admin/faculty?search={marker}", headers=_h(token))
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == f"Alice {marker}"


def test_admin_can_filter_faculty(client):
    token = _admin_token(client)
    _register_faculty(client, designation="Professor")
    _register_faculty(client, designation="Assistant Professor")
    resp = client.get("/api/admin/faculty?designation=Professor", headers=_h(token))
    body = resp.json()
    assert all(item["designation"] == "Professor" for item in body["items"])


def test_admin_can_view_faculty(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    resp = client.get(f"/api/admin/faculty/{info['faculty_id']}", headers=_h(token))
    assert resp.status_code == 200
    assert resp.json()["faculty_id"] == info["faculty_id"]


def test_admin_can_update_faculty(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    orcid = f"0000-0002-{uuid.uuid4().hex[:8]}"
    resp = client.put(
        f"/api/admin/faculty/{info['faculty_id']}",
        headers=_h(token),
        json={"designation": "Associate Professor", "orcid_id": orcid},
    )
    assert resp.status_code == 200
    assert resp.json()["designation"] == "Associate Professor"
    assert resp.json()["orcid_id"] == orcid


def test_admin_can_activate_deactivate_faculty(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    resp = client.patch(
        f"/api/admin/faculty/{info['faculty_id']}/status",
        headers=_h(token),
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# --- Rules -------------------------------------------------------------------

def test_admin_can_list_rules(client):
    token = _admin_token(client)
    resp = client.get("/api/admin/rules", headers=_h(token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 19


def test_admin_can_create_rule(client):
    token = _admin_token(client)
    code = _rule_code()
    resp = client.post(
        "/api/admin/rules",
        headers=_h(token),
        json={"rule_code": code, "name": "Test Rule", "publication_type": "research_publication", "points": 5},
    )
    assert resp.status_code == 201
    assert resp.json()["rule_code"] == code


def test_duplicate_rule_code_rejected(client):
    token = _admin_token(client)
    code = _rule_code()
    payload = {"rule_code": code, "name": "Dup Rule", "points": 5}
    assert client.post("/api/admin/rules", headers=_h(token), json=payload).status_code == 201
    resp = client.post("/api/admin/rules", headers=_h(token), json=payload)
    assert resp.status_code == 409


def test_admin_can_update_rule(client):
    token = _admin_token(client)
    created = client.post(
        "/api/admin/rules",
        headers=_h(token),
        json={"rule_code": _rule_code(), "name": "U", "points": 5},
    ).json()
    resp = client.put(
        f"/api/admin/rules/{created['rule_id']}", headers=_h(token), json={"points": 7}
    )
    assert resp.status_code == 200
    assert resp.json()["points"] == 7


def test_admin_can_deactivate_rule(client):
    token = _admin_token(client)
    created = client.post(
        "/api/admin/rules",
        headers=_h(token),
        json={"rule_code": _rule_code(), "name": "D", "points": 5},
    ).json()
    resp = client.patch(
        f"/api/admin/rules/{created['rule_id']}/status",
        headers=_h(token),
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_negative_points_rejected(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/rules",
        headers=_h(token),
        json={"rule_code": _rule_code(), "name": "N", "points": -5},
    )
    assert resp.status_code == 400


def test_invalid_effective_dates_rejected(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/rules",
        headers=_h(token),
        json={
            "rule_code": _rule_code(),
            "name": "D",
            "points": 5,
            "effective_from": "2026-01-01",
            "effective_to": "2025-01-01",
        },
    )
    assert resp.status_code == 400


# --- Eligibility -------------------------------------------------------------

def test_admin_can_list_eligibility_rules(client):
    token = _admin_token(client)
    resp = client.get("/api/admin/eligibility-rules", headers=_h(token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 3


def test_admin_can_create_update_eligibility_rule(client):
    token = _admin_token(client)
    designation = f"Lecturer {uuid.uuid4().hex[:6]}"
    created = client.post(
        "/api/admin/eligibility-rules",
        headers=_h(token),
        json={"designation": designation, "minimum_points": 50},
    )
    assert created.status_code == 201
    resp = client.put(
        f"/api/admin/eligibility-rules/{created.json()['eligibility_rule_id']}",
        headers=_h(token),
        json={"minimum_points": 60},
    )
    assert resp.status_code == 200
    assert resp.json()["minimum_points"] == 60


def test_negative_minimum_points_rejected(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/eligibility-rules",
        headers=_h(token),
        json={"designation": "Lecturer", "minimum_points": -1},
    )
    assert resp.status_code == 400


# --- Summary -----------------------------------------------------------------

def test_admin_summary_counts(client):
    token = _admin_token(client)
    _register_faculty(client)
    resp = client.get("/api/admin/summary", headers=_h(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["faculty_count"] >= 1
    assert isinstance(body["publication_count"], int)
    assert isinstance(body["academic_year_count"], int)
    assert "current_academic_year" in body


# --- Admin audit logs (Step: admin portal) ----------------------------------

def test_admin_can_list_audit_logs(client):
    admin = _admin_token(client)
    # An admin action that is written to the audit trail.
    created = client.post(
        "/api/admin/departments",
        headers=_h(admin),
        json={"name": "Audit Dept", "code": _code()},
    )
    assert created.status_code == 201
    resp = client.get("/api/admin/audit-logs?page=1&page_size=10", headers=_h(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert all(k in body for k in ("items", "page", "page_size", "total", "total_pages"))
    assert isinstance(body["items"], list)
    assert body["total"] >= 1
    # No secrets leak in audit content.
    import json as _json
    assert "password" not in _json.dumps(body).lower()


def test_audit_logs_require_admin(client):
    info = _register_faculty(client)
    assert client.get("/api/admin/audit-logs", headers=_h(info["token"])).status_code == 403
    assert client.get("/api/admin/audit-logs").status_code == 401


# --- Role escalation protection ---------------------------------------------

def test_public_registration_cannot_create_admin(client):
    email = f"esc_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Escalation Attempt",
            "role": "admin",  # must be ignored
            "department_id": "MCA",
            "designation": "Assistant Professor",
            "is_active": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "faculty"
    stored = mongodb.get_collection(USERS).find_one({"email": email})
    assert stored["role"] == "faculty"
    # The new account still cannot reach admin endpoints.
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    assert client.get("/api/admin/summary", headers=_h(token)).status_code == 403


# --- Admin account management -----------------------------------------------

def _admin_account_payload(email=None):
    return {
        "name": "Second Administrator",
        "email": email or f"newadmin_{uuid.uuid4().hex[:8]}@example.com",
        "password": PASSWORD,
    }


def test_unauthenticated_cannot_create_admin(client):
    resp = client.post("/api/admin/accounts", json=_admin_account_payload())
    assert resp.status_code == 401


def test_faculty_cannot_create_admin(client):
    info = _register_faculty(client)
    resp = client.post(
        "/api/admin/accounts", headers=_h(info["token"]), json=_admin_account_payload()
    )
    assert resp.status_code == 403


def test_admin_can_create_admin(client):
    admin = _admin_token(client)
    payload = _admin_account_payload()
    resp = client.post("/api/admin/accounts", headers=_h(admin), json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == payload["email"]
    assert "password" not in json.dumps(body).lower()
    assert "password_hash" not in json.dumps(body)

    stored = mongodb.get_collection(USERS).find_one({"email": payload["email"]})
    assert stored["role"] == "admin"
    assert stored["password_hash"].startswith("$2")
    assert stored["password_hash"] != PASSWORD

    # The new administrator can sign in and reach admin endpoints.
    login = client.post(
        "/api/auth/login", json={"email": payload["email"], "password": PASSWORD}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get("/api/admin/summary", headers=_h(token)).status_code == 200


def test_duplicate_admin_email_rejected(client):
    admin = _admin_token(client)
    payload = _admin_account_payload()
    assert client.post("/api/admin/accounts", headers=_h(admin), json=payload).status_code == 201
    duplicate = client.post("/api/admin/accounts", headers=_h(admin), json=payload)
    assert duplicate.status_code == 409


def test_admin_creation_cannot_promote_existing_faculty(client):
    info = _register_faculty(client)
    admin = _admin_token(client)
    resp = client.post(
        "/api/admin/accounts",
        headers=_h(admin),
        json={"email": info["email"], "password": PASSWORD},
    )
    assert resp.status_code == 409
    stored = mongodb.get_collection(USERS).find_one({"email": info["email"]})
    assert stored["role"] == "faculty"


def test_create_admin_invalid_input_rejected(client):
    admin = _admin_token(client)
    assert client.post(
        "/api/admin/accounts",
        headers=_h(admin),
        json={"email": "not-an-email", "password": "short"},
    ).status_code == 400
    assert client.post(
        "/api/admin/accounts",
        headers=_h(admin),
        json={"email": _admin_account_payload()["email"], "password": "onlyletters"},
    ).status_code == 400


def test_list_admin_accounts(client):
    admin = _admin_token(client)
    created = client.post(
        "/api/admin/accounts", headers=_h(admin), json=_admin_account_payload()
    ).json()
    resp = client.get("/api/admin/accounts", headers=_h(admin))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["email"] == created["email"] for item in body["items"])
    assert "password" not in json.dumps(body).lower()


def test_faculty_cannot_list_admin_accounts(client):
    info = _register_faculty(client)
    assert client.get("/api/admin/accounts", headers=_h(info["token"])).status_code == 403
    assert client.get("/api/admin/accounts").status_code == 401
