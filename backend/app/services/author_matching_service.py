"""Deterministic author-to-faculty matching (no automatic identity changes).

Only reports evidence; it never mutates faculty identity fields.
"""

from typing import Optional

from app.utils.author_matching import emails_equal, normalize_name, normalize_orcid

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}

# User-facing result category derived from confidence.
_RESULT_BY_CONFIDENCE = {"high": "strong", "medium": "uncertain", "low": "none"}


def _result(confidence: str) -> str:
    return _RESULT_BY_CONFIDENCE.get(confidence, "none")


def _given_family_match(author: dict, faculty: dict) -> bool:
    given = normalize_name(author.get("given_name"))
    family = normalize_name(author.get("family_name"))
    if not given or not family:
        return False
    faculty_name = normalize_name(faculty.get("name"))
    return (f"{given} {family}" == faculty_name) or (
        f"{family} {given}" == faculty_name
    )


def match_author(author: dict, faculty: dict) -> dict:
    """Compare an external author against a faculty member.

    Returns ``{matched, confidence, result, matching_factors, warnings}`` where
    ``result`` is one of ``strong`` / ``uncertain`` / ``none``.
    """
    factors: list[str] = []
    warnings: list[str] = []

    # 1. ORCID — strongest signal.
    external_orcid = normalize_orcid(author.get("orcid_id"))
    faculty_orcid = normalize_orcid(faculty.get("orcid_id"))
    if external_orcid and faculty_orcid and external_orcid == faculty_orcid:
        return {
            "matched": True,
            "confidence": "high",
            "result": "strong",
            "matching_factors": ["orcid_id"],
            "warnings": [],
        }

    # 2. Verified email — reliable only when the metadata actually carries one.
    if emails_equal(author.get("email"), faculty.get("email")):
        return {
            "matched": True,
            "confidence": "high",
            "result": "strong",
            "matching_factors": ["email"],
            "warnings": [],
        }

    # 3. Scopus Author ID.
    external_scopus = author.get("scopus_author_id")
    faculty_scopus = faculty.get("scopus_author_id")
    if external_scopus and faculty_scopus and str(external_scopus) == str(faculty_scopus):
        factors.append("scopus_author_id")

    # 4. Web of Science Researcher ID.
    external_wos = author.get("web_of_science_researcher_id")
    faculty_wos = faculty.get("web_of_science_researcher_id")
    if external_wos and faculty_wos and str(external_wos) == str(faculty_wos):
        factors.append("web_of_science_researcher_id")

    if "scopus_author_id" in factors or "web_of_science_researcher_id" in factors:
        return {
            "matched": True,
            "confidence": "high",
            "result": "strong",
            "matching_factors": factors,
            "warnings": [],
        }

    # 5. Exact normalized full name.
    external_name = normalize_name(author.get("name"))
    faculty_name = normalize_name(faculty.get("name"))
    if external_name and faculty_name and external_name == faculty_name:
        factors.append("exact_name")
        if author.get("affiliation"):
            factors.append("affiliation")
        return {
            "matched": True,
            "confidence": "medium",
            "result": "uncertain",
            "matching_factors": factors,
            "warnings": ["Manual confirmation recommended (name-based match)"],
        }

    # 6. Given/family comparison (still requires BOTH names).
    if _given_family_match(author, faculty):
        return {
            "matched": True,
            "confidence": "medium",
            "result": "uncertain",
            "matching_factors": ["given_family"],
            "warnings": ["Manual confirmation recommended (name-based match)"],
        }

    return {
        "matched": False,
        "confidence": "low",
        "result": "none",
        "matching_factors": factors,
        "warnings": ["No reliable identity match found"],
    }


def match_work_authors(faculty: dict, authors: Optional[list]) -> dict:
    """Return the highest-confidence match across a work's author list."""
    best: Optional[dict] = None
    for author in authors or []:
        if not isinstance(author, dict):
            continue
        result = match_author(author, faculty)
        if best is None or _CONFIDENCE_RANK.get(result["confidence"], 0) > _CONFIDENCE_RANK.get(
            best["confidence"], 0
        ):
            best = result
    if best is None:
        return {
            "matched": False,
            "confidence": "low",
            "result": "none",
            "matching_factors": [],
            "warnings": ["No authors available to compare"],
        }
    return best
