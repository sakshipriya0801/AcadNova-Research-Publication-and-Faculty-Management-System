"""Points calculation, faculty totals and eligibility.

Uses the configurable rule engine (Step 6A) — point values are never
hard-coded here; they come from the ``publication_rules`` collection and the
eligibility thresholds from ``eligibility_rules``.

Only publications with ``verification_status == "verified"`` contribute to
official faculty points.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status

from app.database import mongodb
from app.models.collections import ACADEMIC_YEARS, FACULTY, FACULTY_POINTS, PUBLICATIONS
from app.rules.rule_engine import rule_specificity
from app.services import rule_service

# publication_type -> category key used in category totals.
CATEGORY_BY_TYPE = {
    "research_publication": "research_publication",
    "collaborative_publication": "research_publication",
    "book_editor": "book",
    "book_chapter": "book",
    "conference_proceeding": "conference",
    "patent": "patent",
    "copyright": "copyright",
    "project": "project",
    "consultancy": "project",
    "startup": "other",
    "other": "other",
}

# category key -> faculty_points document field name.
CATEGORY_FIELDS = {
    "research_publication": "research_publication_points",
    "book": "book_points",
    "conference": "conference_points",
    "patent": "patent_points",
    "copyright": "copyright_points",
    "project": "project_points",
    "other": "other_points",
}

CATEGORY_KEYS = [
    "research_publication",
    "book",
    "conference",
    "patent",
    "copyright",
    "project",
    "other",
]


def _faculty_collection():
    return mongodb.get_collection(FACULTY)


def _publications_collection():
    return mongodb.get_collection(PUBLICATIONS)


def _points_collection():
    return mongodb.get_collection(FACULTY_POINTS)


def _category_for(publication_type) -> str:
    return CATEGORY_BY_TYPE.get(publication_type, "other")


def _zero_result(reason: str, needs_review: bool = False) -> dict:
    return {
        "points": 0,
        "rule_id": None,
        "rule_code": None,
        "rule_name": None,
        "reason": reason,
        "needs_review": needs_review,
        "max_claims_per_year": None,
    }


def calculate_publication_points(
    publication: dict,
    faculty: Optional[dict] = None,
    academic_year: Optional[dict] = None,
) -> dict:
    """Return the points a single publication contributes (pure, no writes).

    The returned mapping contains ``points``, ``rule_id``, ``rule_code``,
    ``rule_name``, ``reason``, ``needs_review`` and ``max_claims_per_year``.
    """
    status_value = publication.get("verification_status")
    if status_value != "verified":
        return _zero_result(f"Publication is not verified (status: {status_value})")

    matches = rule_service.find_matching_rules(publication, faculty, academic_year)
    if not matches:
        return _zero_result("No matching rule")

    # Deterministic selection: the most specific rule wins.  A tie at the top
    # specificity means the engine cannot safely choose -> needs_review.
    matches.sort(
        key=lambda m: (
            -rule_specificity(m),
            -int(m.get("points", 0)),
            m.get("rule_code") or "",
        )
    )
    top = matches[0]
    if len(matches) > 1 and rule_specificity(matches[1]) == rule_specificity(top):
        return _zero_result(
            "Multiple rules match with equal specificity; needs review",
            needs_review=True,
        )

    return {
        "points": int(top.get("points", 0)),
        "rule_id": top.get("rule_id"),
        "rule_code": top.get("rule_code"),
        "rule_name": top.get("name"),
        "reason": top.get("reason") or top.get("name"),
        "needs_review": False,
        "max_claims_per_year": top.get("max_claims_per_year"),
    }


def calculate_faculty_points(
    faculty_id: str, academic_year_id: str, persist: bool = True
) -> dict:
    """Calculate and (optionally) persist a faculty's yearly points.

    Returns totals, category breakdown and the per-publication breakdown.
    """
    faculty = _faculty_collection().find_one({"faculty_id": faculty_id})
    if faculty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found"
        )

    academic_year = mongodb.get_collection(ACADEMIC_YEARS).find_one(
        {"academic_year_id": academic_year_id}
    )
    if academic_year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found"
        )

    publications = list(
        _publications_collection().find(
            {"faculty_id": faculty_id, "academic_year_id": academic_year_id}
        )
    )
    publications.sort(
        key=lambda p: (
            p.get("publication_date") or datetime.min.replace(tzinfo=timezone.utc),
            p.get("publication_id") or "",
        )
    )

    category_totals = {key: 0 for key in CATEGORY_KEYS}
    rule_claims: dict[str, int] = {}
    breakdown: list[dict] = []

    for publication in publications:
        if publication.get("verification_status") != "verified":
            continue

        result = calculate_publication_points(publication, faculty, academic_year)
        rule_code = result.get("rule_code")
        max_claims = result.get("max_claims_per_year")

        if result["points"] > 0 and max_claims is not None:
            used = rule_claims.get(rule_code, 0)
            if used >= max_claims:
                result = {
                    "points": 0,
                    "rule_id": result["rule_id"],
                    "rule_code": rule_code,
                    "rule_name": result["rule_name"],
                    "reason": f"Maximum yearly claims reached for this rule ({max_claims})",
                    "needs_review": False,
                    "max_claims_per_year": max_claims,
                }
            else:
                rule_claims[rule_code] = used + 1

        if result["points"] > 0:
            category = _category_for(publication.get("publication_type"))
            category_totals[category] += result["points"]

        breakdown.append(
            {
                "publication_id": publication.get("publication_id"),
                "title": publication.get("title"),
                "publication_type": publication.get("publication_type"),
                "publication_date": publication.get("publication_date"),
                "points": result["points"],
                "rule_code": result["rule_code"],
                "rule_name": result["rule_name"],
                "reason": result["reason"],
            }
        )

    total = sum(category_totals.values())
    result = {
        "faculty_id": faculty_id,
        "academic_year_id": academic_year_id,
        "designation": faculty.get("designation"),
        "total_points": total,
        "research_publication_points": category_totals["research_publication"],
        "book_points": category_totals["book"],
        "conference_points": category_totals["conference"],
        "patent_points": category_totals["patent"],
        "copyright_points": category_totals["copyright"],
        "project_points": category_totals["project"],
        "other_points": category_totals["other"],
        "last_calculated_at": datetime.now(timezone.utc),
        "publications": breakdown,
    }

    if persist:
        _persist_faculty_points(result)

    return result


def _persist_faculty_points(result: dict) -> None:
    collection = _points_collection()
    now = result["last_calculated_at"]
    collection.update_one(
        {"faculty_id": result["faculty_id"], "academic_year_id": result["academic_year_id"]},
        {
            "$set": {
                "total_points": result["total_points"],
                "research_publication_points": result["research_publication_points"],
                "book_points": result["book_points"],
                "conference_points": result["conference_points"],
                "patent_points": result["patent_points"],
                "copyright_points": result["copyright_points"],
                "project_points": result["project_points"],
                "other_points": result["other_points"],
                "last_calculated_at": now,
            },
            "$setOnInsert": {
                "faculty_points_id": str(uuid4()),
                "faculty_id": result["faculty_id"],
                "academic_year_id": result["academic_year_id"],
            },
        },
        upsert=True,
    )


def calculate_eligibility(designation: Optional[str], total_points: int) -> dict:
    """Return the eligibility outcome for a designation and point total."""
    if not designation:
        return {
            "eligible": False,
            "required_points": None,
            "total_points": total_points,
            "remaining_points": None,
            "designation": designation,
            "reason": "No eligibility rule configured for this designation",
        }

    eligibility_rule = rule_service.find_eligibility_rule(designation)
    if eligibility_rule is None:
        return {
            "eligible": False,
            "required_points": None,
            "total_points": total_points,
            "remaining_points": None,
            "designation": designation,
            "reason": "No eligibility rule configured for this designation",
        }

    required = int(eligibility_rule.get("minimum_points", 0))
    remaining = max(0, required - total_points)
    return {
        "eligible": total_points >= required,
        "required_points": required,
        "total_points": total_points,
        "remaining_points": remaining,
        "designation": designation,
        "reason": None,
    }


def get_points_summary(faculty_id: str, academic_year_id: str) -> dict:
    """Compute a fresh summary (never stale) without persisting."""
    result = calculate_faculty_points(faculty_id, academic_year_id, persist=False)
    eligibility = calculate_eligibility(result["designation"], result["total_points"])
    return _build_summary(result, eligibility)


def recalculate_points(faculty_id: str, academic_year_id: str) -> dict:
    """Compute and persist the summary."""
    result = calculate_faculty_points(faculty_id, academic_year_id, persist=True)
    eligibility = calculate_eligibility(result["designation"], result["total_points"])
    return _build_summary(result, eligibility)


def get_points_breakdown(faculty_id: str, academic_year_id: str) -> list[dict]:
    """Return the verified-publication breakdown for a faculty/year."""
    result = calculate_faculty_points(faculty_id, academic_year_id, persist=False)
    return result["publications"]


def _build_summary(result: dict, eligibility: dict) -> dict:
    return {
        "faculty_id": result["faculty_id"],
        "academic_year_id": result["academic_year_id"],
        "total_points": result["total_points"],
        "category_points": {
            "research_publication": result["research_publication_points"],
            "book": result["book_points"],
            "conference": result["conference_points"],
            "patent": result["patent_points"],
            "copyright": result["copyright_points"],
            "project": result["project_points"],
            "other": result["other_points"],
        },
        "eligibility": eligibility,
    }
