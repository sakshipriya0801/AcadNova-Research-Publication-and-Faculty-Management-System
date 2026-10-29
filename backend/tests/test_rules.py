"""Rule-engine foundation tests (Step 6A)."""

import uuid
from datetime import datetime

import pytest

from app.database import mongodb
from app.models.collections import ELIGIBILITY_RULES, PUBLICATION_RULES
from app.services import rule_service
from scripts.seed_rules import (
    PUBLICATION_RULES_SEED,
    seed_eligibility_rules,
    seed_publication_rules,
)


@pytest.fixture(autouse=True)
def _seed_rules(client):
    seed_publication_rules()
    seed_eligibility_rules()
    yield


def _publication(**overrides) -> dict:
    pub = {
        "publication_type": "research_publication",
        "indexing": None,
        "faculty_author_position": None,
        "is_corresponding_author": False,
        "collaboration_type": None,
        "publication_date": datetime(2025, 8, 15),
    }
    pub.update(overrides)
    return pub


def _matched_codes(publication) -> set:
    matches = rule_service.find_matching_rules(publication)
    return {m["rule_code"] for m in matches}


def test_rule_seeding_works(client):
    codes = {
        doc["rule_code"]
        for doc in mongodb.get_collection(PUBLICATION_RULES).find({}, {"rule_code": 1})
    }
    seed_codes = {rule["rule_code"] for rule in PUBLICATION_RULES_SEED}
    assert seed_codes.issubset(codes)


def test_seed_idempotent(client):
    seed_publication_rules()
    count_1 = mongodb.get_collection(PUBLICATION_RULES).count_documents({})
    seed_publication_rules()
    count_2 = mongodb.get_collection(PUBLICATION_RULES).count_documents({})

    assert count_1 == count_2

    codes = [
        doc["rule_code"]
        for doc in mongodb.get_collection(PUBLICATION_RULES).find({}, {"rule_code": 1})
    ]
    assert len(codes) == len(set(codes))


def test_first_author_matches_rule_001(client):
    codes = _matched_codes(_publication(indexing=["Scopus"], faculty_author_position=1))
    assert "RULE-001" in codes


def test_corresponding_author_matches_rule_001(client):
    codes = _matched_codes(
        _publication(
            indexing=["Scopus"],
            faculty_author_position=3,
            is_corresponding_author=True,
        )
    )
    assert "RULE-001" in codes


def test_third_author_matches_rule_002(client):
    codes = _matched_codes(
        _publication(indexing=["Scopus"], faculty_author_position=3)
    )
    assert "RULE-002" in codes


def test_pubmed_indexing_matches(client):
    codes = _matched_codes(
        _publication(indexing=["PubMed"], faculty_author_position=1)
    )
    assert "RULE-001" in codes


def test_scopus_indexing_matches(client):
    codes = _matched_codes(
        _publication(indexing=["Scopus"], faculty_author_position=1)
    )
    assert "RULE-001" in codes


def test_multiple_indexing_values_work(client):
    codes = _matched_codes(
        _publication(
            indexing=["Scopus", "Web of Science"], faculty_author_position=1
        )
    )
    assert "RULE-001" in codes


def test_indexing_is_case_insensitive(client):
    codes = _matched_codes(_publication(indexing=["scopus"], faculty_author_position=1))
    assert "RULE-001" in codes


def test_book_editor_indexed_matches_rule_006(client):
    codes = _matched_codes(
        _publication(publication_type="book_editor", indexing=["Scopus"])
    )
    assert "RULE-006" in codes


def test_book_chapter_indexed_matches_rule_007(client):
    codes = _matched_codes(
        _publication(publication_type="book_chapter", indexing=["Scopus"])
    )
    assert "RULE-007" in codes


def test_isbn_book_editor_max_claims(client):
    rule = mongodb.get_collection(PUBLICATION_RULES).find_one(
        {"rule_code": "RULE-008"}
    )
    assert rule["max_claims_per_year"] == 1


def test_isbn_book_chapter_max_claims(client):
    rule = mongodb.get_collection(PUBLICATION_RULES).find_one(
        {"rule_code": "RULE-009"}
    )
    assert rule["max_claims_per_year"] == 1


def test_conference_rules_yearly_limit(client):
    rule_010 = mongodb.get_collection(PUBLICATION_RULES).find_one(
        {"rule_code": "RULE-010"}
    )
    rule_011 = mongodb.get_collection(PUBLICATION_RULES).find_one(
        {"rule_code": "RULE-011"}
    )
    assert rule_010["max_claims_per_year"] == 1
    assert rule_011["max_claims_per_year"] == 1


def test_inactive_rules_do_not_match(client):
    collection = mongodb.get_collection(PUBLICATION_RULES)
    collection.update_one({"rule_code": "RULE-001"}, {"$set": {"is_active": False}})
    try:
        codes = _matched_codes(
            _publication(indexing=["Scopus"], faculty_author_position=1)
        )
        assert "RULE-001" not in codes
    finally:
        collection.update_one({"rule_code": "RULE-001"}, {"$set": {"is_active": True}})


def test_effective_dates_respected(client):
    collection = mongodb.get_collection(PUBLICATION_RULES)
    collection.insert_one(
        {
            "rule_id": str(uuid.uuid4()),
            "rule_code": "RULE-TEST-FUTURE",
            "name": "Future-dated rule",
            "publication_type": "research_publication",
            "indexing": ["Scopus"],
            "author_positions": None,
            "corresponding_author_required": False,
            "points": 999,
            "is_active": True,
            "effective_from": datetime(2030, 1, 1),
            "effective_to": None,
        }
    )
    try:
        codes = _matched_codes(
            _publication(
                indexing=["Scopus"],
                publication_date=datetime(2025, 8, 15),
            )
        )
        assert "RULE-TEST-FUTURE" not in codes
    finally:
        collection.delete_one({"rule_code": "RULE-TEST-FUTURE"})


def test_eligibility_rules_seeded(client):
    rules = rule_service.list_eligibility_rules()
    by_designation = {r["designation"]: r["minimum_points"] for r in rules}

    assert by_designation["assistant professor"] == 100
    assert by_designation["associate professor"] == 200
    assert by_designation["professor"] == 200


def test_eligibility_seed_idempotent(client):
    seed_eligibility_rules()
    designations = {
        doc["designation"]
        for doc in mongodb.get_collection(ELIGIBILITY_RULES).find({}, {"designation": 1})
    }
    assert {"assistant professor", "associate professor", "professor"}.issubset(
        designations
    )
