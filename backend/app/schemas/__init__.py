"""Pydantic schemas for API request/response validation and documents."""

from app.schemas.academic_year import AcademicYear
from app.schemas.audit_log import AuditLog
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.department import Department
from app.schemas.document import Document
from app.schemas.eligibility_rule import EligibilityRule
from app.schemas.faculty import Faculty
from app.schemas.faculty_points import FacultyPoints
from app.schemas.health import HealthResponse
from app.schemas.publication import Publication
from app.schemas.publication_rule import PublicationRule
from app.schemas.user import User
from app.schemas.verification_record import VerificationRecord

__all__ = [
    "AcademicYear",
    "AuditLog",
    "CurrentUserResponse",
    "Department",
    "Document",
    "EligibilityRule",
    "Faculty",
    "FacultyPoints",
    "HealthResponse",
    "LoginRequest",
    "Publication",
    "PublicationRule",
    "RegisterRequest",
    "TokenResponse",
    "User",
    "VerificationRecord",
]
