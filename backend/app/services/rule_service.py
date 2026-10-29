"""Publication rule and eligibility-configuration service.

Manages the ``publication_rules`` and ``eligibility_rules`` collections and
provides the rule-matching entry point used by the points engine, plus admin
CRUD helpers.

This service does NOT calculate faculty totals or update ``faculty_points``.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.database import mongodb
from app.models.collections import ELIGIBILITY_RULES, PUBLICATION_RULES
from app.rules.rule_engine import normalize_designation, rule_matches
from app.utils.dates import to_iso_string


def _rules_collection():
    return mongodb.get_collection(PUBLICATION_RULES)


def _eligibility_collection():
    return mongodb.get_collection(ELIGIBILITY_RULES)


def _enum_value(value):
    return value.value if isinstance(value, Enum) else value


# --- Publication rules -------------------------------------------------------

def create_rule(rule_data: dict) -> dict:
    """Insert a new publication rule (admin)."""
    if rule_data.get("rule_code"):
        if get_rule_by_code(rule_data["rule_code"]):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Rule code '{rule_data['rule_code']}' already exists",
            )

    if rule_data.get("publication_type") is not None:
        rule_data["publication_type"] = _enum_value(rule_data["publication_type"])
    if "effective_from" in rule_data:
        rule_data["effective_from"] = to_iso_string(rule_data["effective_from"])
    if "effective_to" in rule_data:
        rule_data["effective_to"] = to_iso_string(rule_data["effective_to"])

    now = datetime.now(timezone.utc)
    rule_data.setdefault("rule_id", str(uuid4()))
    rule_data.setdefault("created_at", now)
    rule_data.setdefault("updated_at", now)
    _rules_collection().insert_one(rule_data)
    return rule_data


def get_rule(rule_id: str) -> Optional[dict]:
    return _rules_collection().find_one({"rule_id": rule_id})


def get_rule_by_code(rule_code: str) -> Optional[dict]:
    return _rules_collection().find_one({"rule_code": rule_code})


def list_rules(active_only: bool = False) -> list[dict]:
    query = {"is_active": True} if active_only else {}
    return list(_rules_collection().find(query))


def update_rule(rule_id: str, fields: dict) -> Optional[dict]:
    existing = get_rule(rule_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")

    if "rule_code" in fields and fields["rule_code"]:
        code = fields["rule_code"]
        dup = _rules_collection().find_one(
            {"rule_code": code, "rule_id": {"$ne": rule_id}}
        )
        if dup:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"Rule code '{code}' already exists"
            )

    if "publication_type" in fields and fields["publication_type"] is not None:
        fields["publication_type"] = _enum_value(fields["publication_type"])
    if "effective_from" in fields:
        fields["effective_from"] = to_iso_string(fields["effective_from"])
    if "effective_to" in fields:
        fields["effective_to"] = to_iso_string(fields["effective_to"])

    fields["updated_at"] = datetime.now(timezone.utc)
    return _rules_collection().find_one_and_update(
        {"rule_id": rule_id}, {"$set": fields}, return_document=ReturnDocument.AFTER
    )


def deactivate_rule(rule_id: str) -> bool:
    result = _rules_collection().update_one(
        {"rule_id": rule_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )
    return result.matched_count > 0


# --- Rule matching -----------------------------------------------------------

def find_matching_rules(
    publication: dict,
    faculty: Optional[dict] = None,
    academic_year: Optional[dict] = None,
) -> list[dict]:
    """Return all active rules that apply to the given publication.

    Each entry is the full rule document with an added ``reason`` key.  The
    rule-selection/point-awarding strategy is implemented in the points engine;
    here all applicable rules are returned.
    """
    matches: list[dict] = []
    for rule in _rules_collection().find({"is_active": True}):
        reason = rule_matches(rule, publication, faculty, academic_year)
        if reason:
            match = dict(rule)
            match["reason"] = reason
            matches.append(match)
    return matches


# --- Eligibility configuration -----------------------------------------------

def list_eligibility_rules(active_only: bool = True) -> list[dict]:
    query = {"is_active": True} if active_only else {}
    return list(_eligibility_collection().find(query))


def find_eligibility_rule(designation: str) -> Optional[dict]:
    normalized = normalize_designation(designation)
    return _eligibility_collection().find_one({"designation": normalized})


def get_eligibility_rule_by_id(eligibility_rule_id: str) -> Optional[dict]:
    return _eligibility_collection().find_one(
        {"eligibility_rule_id": eligibility_rule_id}
    )


def create_eligibility_rule(data: dict) -> dict:
    designation = normalize_designation(data["designation"])
    if _eligibility_collection().find_one({"designation": designation}):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Eligibility rule for '{designation}' already exists",
        )

    now = datetime.now(timezone.utc)
    doc = {
        "eligibility_rule_id": str(uuid4()),
        "designation": designation,
        "minimum_points": int(data.get("minimum_points", 0)),
        "is_active": True,
        "effective_from": to_iso_string(data.get("effective_from")),
        "effective_to": to_iso_string(data.get("effective_to")),
        "created_at": now,
        "updated_at": now,
    }
    _eligibility_collection().insert_one(doc)
    return doc


def update_eligibility_rule(eligibility_rule_id: str, fields: dict) -> dict:
    existing = get_eligibility_rule_by_id(eligibility_rule_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Eligibility rule not found")

    if "designation" in fields and fields["designation"] is not None:
        designation = normalize_designation(fields["designation"])
        dup = _eligibility_collection().find_one(
            {
                "designation": designation,
                "eligibility_rule_id": {"$ne": eligibility_rule_id},
            }
        )
        if dup:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Eligibility rule for '{designation}' already exists",
            )
        fields["designation"] = designation

    if "effective_from" in fields:
        fields["effective_from"] = to_iso_string(fields["effective_from"])
    if "effective_to" in fields:
        fields["effective_to"] = to_iso_string(fields["effective_to"])

    fields["updated_at"] = datetime.now(timezone.utc)
    return _eligibility_collection().find_one_and_update(
        {"eligibility_rule_id": eligibility_rule_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )


def set_eligibility_rule_status(eligibility_rule_id: str, is_active: bool) -> dict:
    existing = get_eligibility_rule_by_id(eligibility_rule_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Eligibility rule not found")

    return _eligibility_collection().find_one_and_update(
        {"eligibility_rule_id": eligibility_rule_id},
        {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
