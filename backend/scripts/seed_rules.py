"""Seed the known institutional publication rules and eligibility thresholds.

Usage (from the ``backend/`` directory):

    python -m scripts.seed_rules

The seed is idempotent:

- Rules are upserted by their stable ``rule_code`` using ``$setOnInsert``, so
  running the script twice does NOT create duplicates and does NOT overwrite
  administrator changes to existing rules.
- Eligibility rules are upserted by their normalized ``designation``.

No existing rules are deleted.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Allow running as `python scripts/seed_rules.py` and `python -m scripts.seed_rules`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import mongodb  # noqa: E402
from app.models.collections import (  # noqa: E402
    ELIGIBILITY_RULES,
    PUBLICATION_RULES,
)
from app.rules.rule_engine import normalize_designation  # noqa: E402

# Common indexing set used by several rules.
SCOPUS_WOS_PUBMED = ["Scopus", "Web of Science", "PubMed"]

PUBLICATION_RULES_SEED = [
    {
        "rule_code": "RULE-001",
        "name": "Research Publication — 1st/Corresponding Author — Scopus/WoS/PubMed",
        "publication_type": "research_publication",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": [1],
        "corresponding_author_required": True,
        "collaboration_type": None,
        "points": 100,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Research publication as 1st or corresponding author indexed in Scopus, Web of Science, or PubMed.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-002",
        "name": "Research Publication — 2nd/3rd/4th/5th Co-Author — Scopus/WoS/PubMed",
        "publication_type": "research_publication",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": [2, 3, 4, 5],
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 50,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Research publication as 2nd/3rd/4th/5th co-author indexed in Scopus, Web of Science, or PubMed.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-003",
        "name": "Collaborative Publication — BVDU Faculty — Scopus/WoS/PubMed",
        "publication_type": "collaborative_publication",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 50,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Collaborative paper with other institutions/organizations published in Scopus/WoS/PubMed, applicable to BVDU faculty.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-004",
        "name": "Collaborative Publication — Non-BVDU Faculty — Scopus/WoS/PubMed",
        "publication_type": "collaborative_publication",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 100,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Collaborative paper with other institutions/organizations published in Scopus/WoS/PubMed, applicable to other than BVDU faculty.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-005",
        "name": "Research Publication — 1st/Corresponding Author — ABDC/Regulatory Journal",
        "publication_type": "research_publication",
        "indexing": ["ABDC", "Regulatory Body"],
        "author_positions": [1],
        "corresponding_author_required": True,
        "collaboration_type": None,
        "points": 30,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Research publication as 1st or corresponding author in an ABDC journal or approved regulatory-body journal.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-006",
        "name": "Book Editor — Scopus/WoS/PubMed",
        "publication_type": "book_editor",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 50,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Book editor indexed in Scopus, Web of Science, or PubMed.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-007",
        "name": "Book Chapter — Scopus/WoS/PubMed",
        "publication_type": "book_chapter",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 30,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Book chapter indexed in Scopus, Web of Science, or PubMed.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-008",
        "name": "Book Editor — ISBN (non-indexed)",
        "publication_type": "book_editor",
        "indexing": [],
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 30,
        "max_claims_per_year": 1,
        "eligibility_designation": None,
        "description": "Book editor with ISBN, non-indexed database. Maximum 1 claim per year.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-009",
        "name": "Book Chapter — ISBN (non-indexed)",
        "publication_type": "book_chapter",
        "indexing": [],
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 15,
        "max_claims_per_year": 1,
        "eligibility_designation": None,
        "description": "Book chapter with ISBN, non-indexed database. Maximum 1 claim per year.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-010",
        "name": "Conference Proceedings — Scopus/WoS/PubMed",
        "publication_type": "conference_proceeding",
        "indexing": SCOPUS_WOS_PUBMED,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 30,
        "max_claims_per_year": 1,
        "eligibility_designation": None,
        "description": "Conference proceedings published in Scopus, Web of Science, or PubMed.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-011",
        "name": "Conference Proceedings — ISBN and available online",
        "publication_type": "conference_proceeding",
        "indexing": [],
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 10,
        "max_claims_per_year": 1,
        "eligibility_designation": None,
        "description": "Conference proceedings published with ISBN and available online.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-012",
        "name": "Patent Commercialized / Technology Transfer",
        "publication_type": "patent",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 100,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Patent commercialized / technology transfer; applicants as BV/BVDU faculty.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-013",
        "name": "Utility Patent Granted",
        "publication_type": "patent",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 50,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Utility patent granted; applicants as BV/BVDU faculty.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-014",
        "name": "Utility Patent Published",
        "publication_type": "patent",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 20,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Utility patent published; applicants as BV/BVDU faculty.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-015",
        "name": "Design Patent",
        "publication_type": "patent",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 10,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Design patent.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-016",
        "name": "Copyright Granted",
        "publication_type": "copyright",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 10,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Copyright granted; affiliation as BV/BVDU faculty.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-017",
        "name": "Start-up Incubated at Institute",
        "publication_type": "startup",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 50,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Start-up incubated at the institute.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-018",
        "name": "Extramural/Consultancy Project (>30 Lakhs) — PI",
        "publication_type": "project",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 100,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Extramural project sanctioned or consultancy project over 30 Lakhs — Principal Investigator.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
    {
        "rule_code": "RULE-019",
        "name": "Extramural/Consultancy Project (>30 Lakhs) — Co-PI",
        "publication_type": "project",
        "indexing": None,
        "author_positions": None,
        "corresponding_author_required": False,
        "collaboration_type": None,
        "points": 75,
        "max_claims_per_year": None,
        "eligibility_designation": None,
        "description": "Extramural project sanctioned or consultancy project over 30 Lakhs — Co-Principal Investigator.",
        "is_active": True,
        "effective_from": None,
        "effective_to": None,
    },
]

ELIGIBILITY_RULES_SEED = [
    {"code": "ELIG-ASSISTANT_PROFESSOR", "designation": "assistant professor", "minimum_points": 100},
    {"code": "ELIG-ASSOCIATE_PROFESSOR", "designation": "associate professor", "minimum_points": 200},
    {"code": "ELIG-PROFESSOR", "designation": "professor", "minimum_points": 200},
]

# Publication sub-type that distinguishes otherwise-identical rules (patents,
# projects).  ``None`` for rules that do not need a sub-type.
SUB_TYPE_BY_CODE = {
    "RULE-012": "commercialized",
    "RULE-013": "granted",
    "RULE-014": "published",
    "RULE-015": "design",
    "RULE-018": "pi",
    "RULE-019": "co_pi",
}


def seed_publication_rules() -> int:
    collection = mongodb.get_collection(PUBLICATION_RULES)
    now = datetime.now(timezone.utc)
    inserted = 0
    for rule in PUBLICATION_RULES_SEED:
        doc = dict(rule)
        doc["rule_id"] = str(uuid4())
        doc["sub_type"] = SUB_TYPE_BY_CODE.get(doc["rule_code"])
        doc["created_at"] = now
        doc["updated_at"] = now
        result = collection.update_one(
            {"rule_code": doc["rule_code"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
    return inserted


def seed_eligibility_rules() -> int:
    collection = mongodb.get_collection(ELIGIBILITY_RULES)
    now = datetime.now(timezone.utc)
    inserted = 0
    for rule in ELIGIBILITY_RULES_SEED:
        designation = normalize_designation(rule["designation"])
        doc = {
            "eligibility_rule_id": str(uuid4()),
            "code": rule["code"],
            "designation": designation,
            "minimum_points": rule["minimum_points"],
            "is_active": True,
            "effective_from": None,
            "effective_to": None,
            "created_at": now,
            "updated_at": now,
        }
        result = collection.update_one(
            {"designation": designation},
            {"$setOnInsert": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
    return inserted


def main() -> None:
    mongodb.init_mongodb()
    try:
        try:
            mongodb.create_indexes()
        except Exception as exc:  # indexes are defensive only
            print(f"Warning: index creation skipped: {exc}")

        inserted_rules = seed_publication_rules()
        total_rules = mongodb.get_collection(PUBLICATION_RULES).count_documents({})

        inserted_eligibility = seed_eligibility_rules()
        total_eligibility = mongodb.get_collection(ELIGIBILITY_RULES).count_documents({})

        print(f"Publication rules: {inserted_rules} inserted, {total_rules} total.")
        print(f"Eligibility rules: {inserted_eligibility} inserted, {total_eligibility} total.")
    finally:
        mongodb.close_mongodb()


if __name__ == "__main__":
    main()
