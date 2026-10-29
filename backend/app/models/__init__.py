"""Data models: collection names, index definitions and enums."""

from app.models.collections import (
    ACADEMIC_YEARS,
    AUDIT_LOGS,
    COLLECTIONS,
    DEPARTMENTS,
    DOCUMENTS,
    ELIGIBILITY_RULES,
    FACULTY,
    FACULTY_POINTS,
    INDEXES,
    PUBLICATIONS,
    PUBLICATION_RULES,
    USERS,
    VERIFICATION_RECORDS,
)
from app.models.enums import (
    PublicationSource,
    PublicationType,
    UserRole,
    VerificationStatus,
)

__all__ = [
    "ACADEMIC_YEARS",
    "AUDIT_LOGS",
    "COLLECTIONS",
    "DEPARTMENTS",
    "DOCUMENTS",
    "ELIGIBILITY_RULES",
    "FACULTY",
    "FACULTY_POINTS",
    "INDEXES",
    "PUBLICATIONS",
    "PUBLICATION_RULES",
    "USERS",
    "VERIFICATION_RECORDS",
    "PublicationSource",
    "PublicationType",
    "UserRole",
    "VerificationStatus",
]
