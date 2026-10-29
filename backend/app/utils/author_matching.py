"""Safe author-name and ORCID normalization helpers."""

import re
from typing import Optional

_ORCID_PATTERN = re.compile(r"^(\d{4})-(\d{4})-(\d{4})-(\d{3}[\dX])$", re.IGNORECASE)


def normalize_orcid(value) -> Optional[str]:
    """Return a canonical ORCID (``0000-0002-1825-0097``) or ``None``.

    Handles URL forms (``https://orcid.org/...``, ``https://www.orcid.org/...``)
    and bare identifiers.  The check digit is normalized to uppercase ``X``.
    """
    if value is None:
        return None
    s = str(value).strip()
    s = re.sub(r"^https?://(www\.)?orcid\.org/", "", s)
    s = s.strip().strip("/")
    match = _ORCID_PATTERN.match(s)
    if not match:
        return None
    groups = match.groups()
    return f"{groups[0]}-{groups[1]}-{groups[2]}-{groups[3].upper()}"


def normalize_name(value) -> str:
    """Normalize a person name for comparison.

    Lowercases, collapses whitespace, strips periods (so initials like
    ``"J. R. R. Tolkien"`` and ``"J R R Tolkien"`` match) and handles the
    common reversed ``"Priya, Sakshi"`` form as ``"sakshi priya"``.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        s = " ".join(reversed(parts))
    s = s.replace(".", " ")
    return " ".join(s.lower().split())


def normalize_email(value) -> Optional[str]:
    """Return a canonical, trimmed lowercase email or ``None``."""
    if value is None:
        return None
    s = str(value).strip().lower()
    return s or None


def emails_equal(email1, email2) -> bool:
    e1 = normalize_email(email1)
    e2 = normalize_email(email2)
    return bool(e1 and e2 and e1 == e2)


def names_equal(name1, name2) -> bool:
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    return bool(n1 and n2 and n1 == n2)
