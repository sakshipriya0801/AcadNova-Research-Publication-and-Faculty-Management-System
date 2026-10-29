"""Pure rule-matching logic (no database access).

This module answers the question: "does a publication satisfy a publication
rule?"  It is intentionally free of MongoDB access so the matching logic can be
tested and reused independently.

Matching semantics:

- ``publication_type``: rule value must equal the publication's type (or be
  ``None`` to impose no type condition).
- ``indexing``:
    * ``None`` -> no condition
    * ``[]``  -> publication must be non-indexed (no indexing sources)
    * ``["Scopus", ...]`` -> publication must contain at least one of these
      sources (case-insensitive subset match, never exact-array equality).
- author condition (OR of two qualifiers):
    * ``author_positions`` contains ``faculty_author_position``
    * ``corresponding_author_required`` is true AND
      ``is_corresponding_author`` is true
  If neither is configured, there is no author condition.
- ``collaboration_type``: rule value must equal the publication's collaboration
  type (or be ``None``).
- ``eligibility_designation``: if configured, the faculty's designation must be
  in the list (case/whitespace insensitive).
- effective dates: the publication date must fall within
  ``effective_from``/``effective_to`` when provided.
"""

from datetime import date, datetime
from typing import Optional

_INDEXING_ALIASES = {
    "wos": "web of science",
    "web-of-science": "web of science",
    "web of science": "web of science",
    "scopus": "scopus",
    "pubmed": "pubmed",
    "abdc": "abdc",
    "regulatory": "regulatory body",
    "regulatory body": "regulatory body",
}


def _collapse(value: str) -> str:
    return " ".join(str(value).lower().split())


def normalize_indexing(value) -> str:
    """Return a canonical, case-insensitive indexing source name."""
    collapsed = _collapse(value)
    return _INDEXING_ALIASES.get(collapsed, collapsed)


def normalize_designation(value) -> str:
    """Return a canonical, case/whitespace-insensitive designation."""
    return _collapse(value)


def rule_specificity(rule: dict) -> int:
    """Return a specificity score for deterministic rule selection.

    More restrictive conditions -> higher score.  Used by the points engine to
    prefer the most specific applicable rule.
    """
    score = 0
    if rule.get("publication_type") is not None:
        score += 1
    if rule.get("indexing") is not None:
        score += 1
    if rule.get("author_positions") is not None:
        score += 1
    if rule.get("corresponding_author_required") is True:
        score += 1
    if rule.get("collaboration_type") is not None:
        score += 1
    if rule.get("sub_type") is not None:
        score += 1
    if rule.get("eligibility_designation"):
        score += 1
    return score


def _indexing_matches(rule: dict, publication: dict) -> bool:
    rule_indexing = rule.get("indexing")
    pub_indexing = publication.get("indexing") or []

    if rule_indexing is None:
        return True
    if len(rule_indexing) == 0:
        # "non-indexed" rule: publication must have no indexing sources.
        return len(pub_indexing) == 0

    rule_set = {normalize_indexing(v) for v in rule_indexing}
    pub_set = {normalize_indexing(v) for v in pub_indexing}
    return bool(rule_set & pub_set)


def _author_matches(rule: dict, publication: dict) -> bool:
    positions = rule.get("author_positions")
    requires_corresponding = rule.get("corresponding_author_required") is True

    if positions is None and not requires_corresponding:
        return True

    position_match = (
        positions is not None
        and publication.get("faculty_author_position") in positions
    )
    corresponding_match = (
        requires_corresponding and publication.get("is_corresponding_author") is True
    )
    return position_match or corresponding_match


def _designation_matches(rule: dict, faculty: Optional[dict]) -> bool:
    designations = rule.get("eligibility_designation")
    if not designations:
        return True
    if faculty is None:
        return False
    faculty_designation = faculty.get("designation")
    if faculty_designation is None:
        return False
    normalized = normalize_designation(faculty_designation)
    return normalized in {normalize_designation(d) for d in designations}


def _as_date(value) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    return value


def _effective_dates_match(rule: dict, publication: dict) -> bool:
    effective_from = _as_date(rule.get("effective_from"))
    effective_to = _as_date(rule.get("effective_to"))
    if effective_from is None and effective_to is None:
        return True

    publication_date = _as_date(publication.get("publication_date"))
    if publication_date is None:
        return True

    if effective_from is not None and publication_date < effective_from:
        return False
    if effective_to is not None and publication_date > effective_to:
        return False
    return True


def rule_matches(
    rule: dict,
    publication: dict,
    faculty: Optional[dict] = None,
    academic_year: Optional[dict] = None,
) -> Optional[str]:
    """Return a human-readable reason when the rule matches, else ``None``."""
    if rule.get("publication_type") is not None and rule.get(
        "publication_type"
    ) != publication.get("publication_type"):
        return None
    if not _indexing_matches(rule, publication):
        return None
    if not _author_matches(rule, publication):
        return None
    if rule.get("collaboration_type") is not None and rule.get(
        "collaboration_type"
    ) != publication.get("collaboration_type"):
        return None
    if rule.get("sub_type") is not None and rule.get("sub_type") != publication.get(
        "sub_type"
    ):
        return None
    if not _designation_matches(rule, faculty):
        return None
    if not _effective_dates_match(rule, publication):
        return None
    return rule.get("name") or rule.get("rule_code")
