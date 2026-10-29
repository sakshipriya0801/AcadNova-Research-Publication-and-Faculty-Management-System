"""Publication rule document schema.

Rules make the points system configurable instead of hard-coded.  Each rule
describes a set of conditions (publication type, indexing, author position,
corresponding-author status, collaboration type, designation) and the points
awarded when those conditions are met.

Matching semantics (see ``app/rules/rule_engine.py``):

- ``indexing``:
    * ``None``  -> no indexing condition (matches anything)
    * ``[]``    -> publication must be non-indexed (no indexing sources)
    * ``["Scopus", ...]`` -> publication must contain at least one of these
      sources (case-insensitive, subset match, not exact equality).
- ``author_positions``:
    * ``None``  -> no author-position condition
    * ``[1]``, ``[2, 3, 4, 5]``, ... -> position must be in the list.
- ``corresponding_author_required``: when ``True``, being the corresponding
  author is an *additional* qualifying way to match (used for
  "1st OR corresponding" rules), combined with ``author_positions`` via OR.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from app.models.enums import PublicationType
from app.schemas.common import MongoDocument, utcnow


class PublicationRule(MongoDocument):
    rule_id: Optional[str] = None
    rule_code: Optional[str] = None
    name: str
    publication_type: Optional[PublicationType] = None
    indexing: Optional[list[str]] = None
    author_positions: Optional[list[int]] = None
    corresponding_author_required: bool = False
    collaboration_type: Optional[str] = None
    sub_type: Optional[str] = None
    points: int = 0
    max_claims_per_year: Optional[int] = None
    eligibility_designation: Optional[list[str]] = None
    description: Optional[str] = None
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)
