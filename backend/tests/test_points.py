"""Points calculation, faculty totals and eligibility tests (Step 6B)."""

import uuid
from datetime import datetime

import pytest

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, FACULTY_POINTS, PUBLICATIONS
from app.services import points_service
from scripts.seed_rules import seed_eligibility_rules, seed_publication_rules

PASSWORD = "StrongPassword123"


@pytest.fixture(autouse=True)
def _setup(client):
    seed_publication_rules()
    seed_eligibility_rules()
    yield


def _register_faculty(client, designation="Assistant Professor") -> dict:
    email = f"pts_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "Points Faculty",
            "employee_id": "EMP_" + uuid.uuid4().hex[:6],
            "department_id": "MCA",
            "designation": designation,
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"email": email, "token": token, "faculty_id": reg.json()["faculty_id"]}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _academic_year(name="2025-2026") -> str:
    db = mongodb.get_database()
    existing = db[ACADEMIC_YEARS].find_one({"name": name})
    if existing:
        return existing["academic_year_id"]
    ay_id = str(uuid.uuid4())
    db[ACADEMIC_YEARS].insert_one(
        {
            "academic_year_id": ay_id,
            "name": name,
            "start_date": "2025-07-01",
            "end_date": "2026-06-30",
            "is_current": True,
        }
    )
    return ay_id


def _pub_dict(**overrides) -> dict:
    pub = {
        "publication_id": str(uuid.uuid4()),
        "title": "Publication",
        "publication_type": "research_publication",
        "indexing": ["Scopus"],
        "faculty_author_position": 1,
        "is_corresponding_author": False,
        "sub_type": None,
        "publication_date": datetime(2025, 8, 15),
        "verification_status": "verified",
    }
    pub.update(overrides)
    return pub


def _insert_publication(faculty_id, academic_year_id, **overrides) -> dict:
    pub = _pub_dict(**overrides)
    pub["faculty_id"] = faculty_id
    pub["academic_year_id"] = academic_year_id
    pub["authors"] = ["A", "B"]
    pub["author_count"] = 2
    pub["source"] = "manual"
    pub["points_awarded"] = 0
    pub["publication_year"] = 2025
    mongodb.get_collection(PUBLICATIONS).insert_one(pub)
    return pub


def _calc(pub: dict) -> dict:
    return points_service.calculate_publication_points(pub)


# --- single-publication calculation ------------------------------------------

def test_verified_first_author_scopus_is_100(client):
    result = _calc(_pub_dict(indexing=["Scopus"], faculty_author_position=1))
    assert result["points"] == 100
    assert result["rule_code"] == "RULE-001"


def test_corresponding_author_matches_configured_rule(client):
    result = _calc(
        _pub_dict(
            indexing=["Scopus"], faculty_author_position=3, is_corresponding_author=True
        )
    )
    assert result["points"] == 100
    assert result["rule_code"] == "RULE-001"


def test_third_author_indexed_is_50(client):
    result = _calc(_pub_dict(indexing=["Scopus"], faculty_author_position=3))
    assert result["points"] == 50
    assert result["rule_code"] == "RULE-002"


def test_pending_publication_is_zero(client):
    result = _calc(_pub_dict(verification_status="pending"))
    assert result["points"] == 0


def test_rejected_publication_is_zero(client):
    result = _calc(_pub_dict(verification_status="rejected"))
    assert result["points"] == 0


def test_needs_review_publication_is_zero(client):
    result = _calc(_pub_dict(verification_status="needs_review"))
    assert result["points"] == 0


def test_book_editor_indexed_is_50(client):
    result = _calc(_pub_dict(publication_type="book_editor", indexing=["Scopus"]))
    assert result["points"] == 50
    assert result["rule_code"] == "RULE-006"


def test_book_chapter_indexed_is_30(client):
    result = _calc(_pub_dict(publication_type="book_chapter", indexing=["Scopus"]))
    assert result["points"] == 30
    assert result["rule_code"] == "RULE-007"


def test_patent_granted_is_50(client):
    result = _calc(_pub_dict(publication_type="patent", sub_type="granted", indexing=None))
    assert result["points"] == 50
    assert result["rule_code"] == "RULE-013"


def test_copyright_is_10(client):
    result = _calc(_pub_dict(publication_type="copyright", indexing=None))
    assert result["points"] == 10
    assert result["rule_code"] == "RULE-016"


def test_startup_is_50(client):
    result = _calc(_pub_dict(publication_type="startup", indexing=None))
    assert result["points"] == 50
    assert result["rule_code"] == "RULE-017"


# --- aggregation / category totals -------------------------------------------

def test_multiple_verified_publications_aggregate(client):
    info = _register_faculty(client)
    ay_id = _academic_year()

    _insert_publication(info["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)
    _insert_publication(
        info["faculty_id"], ay_id, indexing=["PubMed"], faculty_author_position=3
    )
    _insert_publication(
        info["faculty_id"], ay_id, publication_type="book_chapter", indexing=["Scopus"]
    )

    result = points_service.calculate_faculty_points(
        info["faculty_id"], ay_id, persist=False
    )
    assert result["total_points"] == 100 + 50 + 30


def test_category_totals_correct(client):
    info = _register_faculty(client)
    ay_id = _academic_year()

    _insert_publication(info["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)  # 100 research
    _insert_publication(info["faculty_id"], ay_id, publication_type="book_chapter", indexing=["Scopus"])  # 30 book
    _insert_publication(info["faculty_id"], ay_id, publication_type="copyright", indexing=None)  # 10 copyright

    result = points_service.calculate_faculty_points(
        info["faculty_id"], ay_id, persist=False
    )
    assert result["research_publication_points"] == 100
    assert result["book_points"] == 30
    assert result["copyright_points"] == 10
    assert result["total_points"] == 140


def test_isbn_book_editor_max_one_per_year(client):
    info = _register_faculty(client)
    ay_id = _academic_year()

    _insert_publication(info["faculty_id"], ay_id, publication_type="book_editor", indexing=[])
    _insert_publication(info["faculty_id"], ay_id, publication_type="book_editor", indexing=[])

    result = points_service.calculate_faculty_points(
        info["faculty_id"], ay_id, persist=False
    )
    assert result["book_points"] == 30  # only first claim counts


def test_isbn_book_chapter_max_one_per_year(client):
    info = _register_faculty(client)
    ay_id = _academic_year()

    _insert_publication(info["faculty_id"], ay_id, publication_type="book_chapter", indexing=[])
    _insert_publication(info["faculty_id"], ay_id, publication_type="book_chapter", indexing=[])

    result = points_service.calculate_faculty_points(
        info["faculty_id"], ay_id, persist=False
    )
    assert result["book_points"] == 15


def test_conference_yearly_limit(client):
    info = _register_faculty(client)
    ay_id = _academic_year()

    _insert_publication(info["faculty_id"], ay_id, publication_type="conference_proceeding", indexing=["Scopus"])
    _insert_publication(info["faculty_id"], ay_id, publication_type="conference_proceeding", indexing=["Scopus"])

    result = points_service.calculate_faculty_points(
        info["faculty_id"], ay_id, persist=False
    )
    assert result["conference_points"] == 30


# --- eligibility --------------------------------------------------------------

def test_eligibility_reads_config(client):
    result = points_service.calculate_eligibility("Assistant Professor", 120)
    assert result["eligible"] is True
    assert result["required_points"] == 100


def test_assistant_professor_threshold(client):
    assert points_service.calculate_eligibility("Assistant Professor", 100)["eligible"] is True
    assert points_service.calculate_eligibility("Assistant Professor", 99)["eligible"] is False


def test_associate_professor_threshold(client):
    assert points_service.calculate_eligibility("Associate Professor", 200)["eligible"] is True
    assert points_service.calculate_eligibility("Associate Professor", 199)["eligible"] is False


def test_professor_threshold(client):
    assert points_service.calculate_eligibility("Professor", 200)["eligible"] is True
    assert points_service.calculate_eligibility("Professor", 150)["eligible"] is False


def test_unknown_designation_safe(client):
    result = points_service.calculate_eligibility(
        f"Nonexistent Designation {uuid.uuid4().hex[:6]}", 50
    )
    assert result["eligible"] is False
    assert result["required_points"] is None
    assert result["remaining_points"] is None
    assert result["reason"]


def test_below_threshold_remaining(client):
    result = points_service.calculate_eligibility("Assistant Professor", 70)
    assert result["eligible"] is False
    assert result["remaining_points"] == 30


def test_equal_threshold_eligible(client):
    result = points_service.calculate_eligibility("Assistant Professor", 100)
    assert result["eligible"] is True
    assert result["remaining_points"] == 0


def test_above_threshold_eligible(client):
    result = points_service.calculate_eligibility("Assistant Professor", 200)
    assert result["eligible"] is True
    assert result["remaining_points"] == 0


# --- API / recalculation ------------------------------------------------------

def test_recalculate_creates_one_record(client):
    info = _register_faculty(client)
    ay_id = _academic_year()
    _insert_publication(info["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)

    resp = client.post(
        "/api/points/recalculate",
        headers=_headers(info["token"]),
        json={"academic_year_id": ay_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_points"] == 100
    assert body["eligibility"]["eligible"] is True

    # recalculate again -> still one record
    client.post(
        "/api/points/recalculate",
        headers=_headers(info["token"]),
        json={"academic_year_id": ay_id},
    )
    records = list(
        mongodb.get_collection(FACULTY_POINTS).find(
            {"faculty_id": info["faculty_id"], "academic_year_id": ay_id}
        )
    )
    assert len(records) == 1


def test_recalculate_updates_existing_record(client):
    info = _register_faculty(client)
    ay_id = _academic_year()
    pub = _insert_publication(info["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)

    client.post(
        "/api/points/recalculate",
        headers=_headers(info["token"]),
        json={"academic_year_id": ay_id},
    )

    # add another verified publication, recalc again
    _insert_publication(info["faculty_id"], ay_id, publication_type="copyright", indexing=None)
    resp = client.post(
        "/api/points/recalculate",
        headers=_headers(info["token"]),
        json={"academic_year_id": ay_id},
    )
    assert resp.json()["total_points"] == 110

    records = list(
        mongodb.get_collection(FACULTY_POINTS).find(
            {"faculty_id": info["faculty_id"], "academic_year_id": ay_id}
        )
    )
    assert len(records) == 1
    assert records[0]["total_points"] == 110


def test_summary_endpoint(client):
    info = _register_faculty(client)
    ay_id = _academic_year()
    _insert_publication(info["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)

    resp = client.get(
        "/api/points/summary",
        headers=_headers(info["token"]),
        params={"academic_year_id": ay_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_points"] == 100
    assert body["category_points"]["research_publication"] == 100
    assert body["eligibility"]["required_points"] == 100


def test_breakdown_endpoint(client):
    info = _register_faculty(client)
    ay_id = _academic_year()
    pub = _insert_publication(info["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)

    resp = client.get(
        "/api/points/breakdown",
        headers=_headers(info["token"]),
        params={"academic_year_id": ay_id},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["publication_id"] == pub["publication_id"]
    assert items[0]["rule_code"] == "RULE-001"


def test_faculty_cannot_calculate_other_faculty(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    ay_id = _academic_year()

    client.post(
        "/api/points/recalculate",
        headers=_headers(info_a["token"]),
        json={"academic_year_id": ay_id},
    )

    records_b = list(
        mongodb.get_collection(FACULTY_POINTS).find({"faculty_id": info_b["faculty_id"]})
    )
    assert records_b == []


def test_faculty_cannot_view_other_breakdown(client):
    info_a = _register_faculty(client)
    info_b = _register_faculty(client)
    ay_id = _academic_year()
    pub_b = _insert_publication(info_b["faculty_id"], ay_id, indexing=["Scopus"], faculty_author_position=1)

    resp = client.get(
        "/api/points/breakdown",
        headers=_headers(info_a["token"]),
        params={"academic_year_id": ay_id},
    )
    ids = {item["publication_id"] for item in resp.json()}
    assert pub_b["publication_id"] not in ids


def test_points_only_for_selected_academic_year(client):
    info = _register_faculty(client)
    ay_2025 = _academic_year("2025-2026")
    ay_2026 = _academic_year("2026-2027")

    _insert_publication(info["faculty_id"], ay_2025, indexing=["Scopus"], faculty_author_position=1)
    _insert_publication(info["faculty_id"], ay_2026, publication_type="copyright", indexing=None)

    resp = client.get(
        "/api/points/summary",
        headers=_headers(info["token"]),
        params={"academic_year_id": ay_2025},
    )
    assert resp.json()["total_points"] == 100  # only 2025-2026 publication
