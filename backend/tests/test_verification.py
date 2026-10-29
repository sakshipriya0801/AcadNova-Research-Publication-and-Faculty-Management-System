"""Publication verification workflow tests (Step 8A)."""

import uuid

import pytest

from app.database import mongodb
from app.models.collections import (
    ACADEMIC_YEARS,
    AUDIT_LOGS,
    PUBLICATIONS,
    USERS,
    VERIFICATION_RECORDS,
)
from app.services import points_service
from app.utils import security
from scripts.seed_rules import seed_eligibility_rules, seed_publication_rules

PASSWORD = "StrongPassword123"


@pytest.fixture(autouse=True)
def _seed(client):
    seed_publication_rules()
    seed_eligibility_rules()
    _ensure_academic_year("2025-2026")
    yield


def _ensure_academic_year(name="2025-2026"):
    db = mongodb.get_database()
    if db[ACADEMIC_YEARS].find_one({"name": name}) is None:
        db[ACADEMIC_YEARS].insert_one(
            {
                "academic_year_id": str(uuid.uuid4()),
                "name": name,
                "start_date": "2025-07-01",
                "end_date": "2026-06-30",
                "is_current": True,
            }
        )


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


def _register_faculty(client) -> dict:
    email = f"vf_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "VF Faculty",
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
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


def _create_publication(client, token, title="Test Publication") -> dict:
    resp = client.post(
        "/api/publications",
        headers=_h(token),
        json={
            "title": title,
            "authors": ["Author One", "Author Two"],
            "publication_type": "research_publication",
            "faculty_author_position": 1,
            "publication_date": "2025-08-15",
            "indexing": ["Scopus"],
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _pub_from_db(publication_id):
    return mongodb.get_collection(PUBLICATIONS).find_one(
        {"publication_id": publication_id}
    )


# --- Authentication ----------------------------------------------------------

def test_unauthenticated_verification_401(client):
    resp = client.post("/api/admin/publications/some-id/verification", json={"action": "verify"})
    assert resp.status_code == 401


def test_faculty_cannot_verify(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(info["token"]),
        json={"action": "verify"},
    )
    assert resp.status_code == 403


def test_admin_can_verify(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])

    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify", "notes": "checked"},
    )
    assert resp.status_code == 200
    assert resp.json()["publication"]["verification_status"] == "verified"


# --- Transitions -------------------------------------------------------------

def test_pending_to_rejected(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])

    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "reject", "reason": "missing evidence"},
    )
    assert resp.status_code == 200
    assert resp.json()["publication"]["verification_status"] == "rejected"


def test_verified_to_rejected(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "reject", "reason": "evidence withdrawn"},
    )
    assert resp.status_code == 200
    assert resp.json()["publication"]["verification_status"] == "rejected"


def test_rejected_to_verified(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "reject", "reason": "missing evidence"},
    )
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    assert resp.status_code == 200
    assert resp.json()["publication"]["verification_status"] == "verified"


def test_same_status_transition_400(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    assert resp.status_code == 400


def test_reject_without_reason_400(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "reject"},
    )
    assert resp.status_code == 400


def test_invalid_action_400(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    resp = client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "approve"},
    )
    assert resp.status_code == 400


def test_nonexistent_publication_404(client):
    token = _admin_token(client)
    resp = client.post(
        "/api/admin/publications/nonexistent-id/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    assert resp.status_code == 404


# --- Authorization / history -------------------------------------------------

def test_faculty_can_see_own_history(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/verification-history",
        headers=_h(info["token"]),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["action"] == "verify"


def test_faculty_cannot_see_other_history(client):
    token = _admin_token(client)
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    pub = _create_publication(client, info_a["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )

    resp = client.get(
        f"/api/publications/{pub['publication_id']}/verification-history",
        headers=_h(info_b["token"]),
    )
    assert resp.status_code == 403


def test_admin_can_see_any_history(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )

    resp = client.get(
        f"/api/admin/publications/{pub['publication_id']}/verification-history",
        headers=_h(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- Audit & records ---------------------------------------------------------

def test_verify_creates_audit_log(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )

    log = mongodb.get_collection(AUDIT_LOGS).find_one(
        {"entity_id": pub["publication_id"], "action": "publication.verify"}
    )
    assert log is not None
    assert log["entity_type"] == "publication"
    assert log["new_value"]["verification_status"] == "verified"


def test_reject_creates_audit_log(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "reject", "reason": "no evidence"},
    )

    log = mongodb.get_collection(AUDIT_LOGS).find_one(
        {"entity_id": pub["publication_id"], "action": "publication.reject"}
    )
    assert log is not None


def test_successful_change_creates_one_record(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])

    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    records = list(
        mongodb.get_collection(VERIFICATION_RECORDS).find(
            {"publication_id": pub["publication_id"]}
        )
    )
    assert len(records) == 1
    assert records[0]["previous_status"] == "pending"
    assert records[0]["new_status"] == "verified"


def test_failed_transition_creates_no_record(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])

    # same-status attempt -> 400
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    records = list(
        mongodb.get_collection(VERIFICATION_RECORDS).find(
            {"publication_id": pub["publication_id"]}
        )
    )
    assert len(records) == 1


# --- Points interaction ------------------------------------------------------

def test_pending_contributes_zero(client):
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    result = points_service.calculate_publication_points(_pub_from_db(pub["publication_id"]))
    assert result["points"] == 0


def test_rejected_contributes_zero(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "reject", "reason": "no evidence"},
    )
    result = points_service.calculate_publication_points(_pub_from_db(pub["publication_id"]))
    assert result["points"] == 0


def test_verified_can_be_included(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    pub = _create_publication(client, info["token"])
    client.post(
        f"/api/admin/publications/{pub['publication_id']}/verification",
        headers=_h(token),
        json={"action": "verify"},
    )
    result = points_service.calculate_publication_points(_pub_from_db(pub["publication_id"]))
    assert result["points"] == 100
    assert result["rule_code"] == "RULE-001"


# --- Admin publication list --------------------------------------------------

def test_admin_list_pagination(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    marker = uuid.uuid4().hex[:8]
    for i in range(3):
        _create_publication(client, info["token"], title=f"Pub {marker} {i}")

    resp = client.get(
        f"/api/admin/publications?search={marker}&page=1&page_size=2", headers=_h(token)
    )
    body = resp.json()
    assert body["page_size"] == 2
    assert body["total"] == 3
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2


def test_admin_list_search(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    marker = uuid.uuid4().hex[:8]
    _create_publication(client, info["token"], title=f"Unique {marker}")
    resp = client.get(f"/api/admin/publications?search={marker}", headers=_h(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


def test_admin_list_filter_status(client):
    token = _admin_token(client)
    info = _register_faculty(client)
    _create_publication(client, info["token"], title="Pending One")
    resp = client.get("/api/admin/publications?verification_status=pending", headers=_h(token))
    assert resp.status_code == 200
    assert all(p["verification_status"] == "pending" for p in resp.json()["items"])


def test_admin_list_sorting(client):
    token = _admin_token(client)
    resp = client.get("/api/admin/publications?sort_by=title&sort_order=asc", headers=_h(token))
    assert resp.status_code == 200


def test_admin_list_requires_admin(client):
    info = _register_faculty(client)
    resp = client.get("/api/admin/publications", headers=_h(info["token"]))
    assert resp.status_code == 403
