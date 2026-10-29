"""Admin management request/response schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import DEPARTMENT_PROGRAMS, DESIGNATIONS, PublicationType
from app.schemas.faculty import FacultyProfileResponse


# --- Academic years ----------------------------------------------------------

class AcademicYearCreate(BaseModel):
    name: str
    start_date: date
    end_date: date


class AcademicYearUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AcademicYearResponse(BaseModel):
    academic_year_id: str
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _coerce_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value


# --- Departments -------------------------------------------------------------

class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    department_id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Faculty -----------------------------------------------------------------

class FacultyAdminUpdate(BaseModel):
    name: Optional[str] = None
    employee_id: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[str] = None
    designation: Optional[str] = None
    orcid_id: Optional[str] = None
    scopus_author_id: Optional[str] = None
    web_of_science_researcher_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    research_interests: Optional[list[str]] = None
    profile_photo_url: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def _lower_email(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value

    @field_validator(
        "employee_id", "department_id", "designation", "orcid_id",
        "scopus_author_id", "web_of_science_researcher_id", "pubmed_id",
        "profile_photo_url", mode="before",
    )
    @classmethod
    def _strip(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("research_interests", mode="before")
    @classmethod
    def _clean_interests(cls, value):
        if value is None:
            return None
        cleaned, seen = [], set()
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped and stripped not in seen:
                    cleaned.append(stripped)
                    seen.add(stripped)
        return cleaned


class FacultyStatusUpdate(BaseModel):
    is_active: bool


class FacultyListResponse(BaseModel):
    items: list[FacultyProfileResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class FacultyCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: str
    designation: str

    @field_validator("email", mode="before")
    @classmethod
    def _lower_email(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be empty")
        return cleaned

    @field_validator("department_id")
    @classmethod
    def _validate_department(cls, value: str) -> str:
        if value not in DEPARTMENT_PROGRAMS:
            raise ValueError("Select a valid department")
        return value

    @field_validator("designation")
    @classmethod
    def _validate_designation(cls, value: str) -> str:
        if value not in DESIGNATIONS:
            raise ValueError("Select a valid designation")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None  # blank -> generate automatically
        if len(cleaned) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isalpha() for char in cleaned):
            raise ValueError("Password must contain at least one letter")
        if not any(char.isdigit() for char in cleaned):
            raise ValueError("Password must contain at least one number")
        return cleaned


class FacultyCreateResponse(FacultyProfileResponse):
    generated_password: Optional[str] = None


class FacultyRejectRequest(BaseModel):
    reason: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def _clean_reason(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class FacultyApplicationResponse(BaseModel):
    faculty_id: str
    name: str
    email: str
    employee_id: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[str] = None
    approval_status: str
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None


class FacultyApplicationListResponse(BaseModel):
    items: list[FacultyApplicationResponse] = Field(default_factory=list)
    page: int = 1
    page_size: int = 50
    total: int = 0
    total_pages: int = 0


# --- Rules -------------------------------------------------------------------

class RuleAdminCreate(BaseModel):
    rule_code: str
    name: str
    publication_type: Optional[PublicationType] = None
    sub_type: Optional[str] = None
    indexing: Optional[list[str]] = None
    author_positions: Optional[list[int]] = None
    corresponding_author_required: bool = False
    collaboration_type: Optional[str] = None
    points: int = Field(0, ge=0)
    max_claims_per_year: Optional[int] = Field(None, ge=1)
    eligibility_designation: Optional[list[str]] = None
    description: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: bool = True

    @field_validator("rule_code", "name", mode="before")
    @classmethod
    def _strip_required(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("value cannot be empty")
        return value


class RuleAdminUpdate(BaseModel):
    rule_code: Optional[str] = None
    name: Optional[str] = None
    publication_type: Optional[PublicationType] = None
    sub_type: Optional[str] = None
    indexing: Optional[list[str]] = None
    author_positions: Optional[list[int]] = None
    corresponding_author_required: Optional[bool] = None
    collaboration_type: Optional[str] = None
    points: Optional[int] = Field(None, ge=0)
    max_claims_per_year: Optional[int] = Field(None, ge=1)
    eligibility_designation: Optional[list[str]] = None
    description: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None


class RuleStatusUpdate(BaseModel):
    is_active: bool


class RuleResponse(BaseModel):
    rule_id: str
    rule_code: Optional[str] = None
    name: str
    publication_type: Optional[PublicationType] = None
    sub_type: Optional[str] = None
    indexing: Optional[list[str]] = None
    author_positions: Optional[list[int]] = None
    corresponding_author_required: bool = False
    collaboration_type: Optional[str] = None
    points: int = 0
    max_claims_per_year: Optional[int] = None
    eligibility_designation: Optional[list[str]] = None
    description: Optional[str] = None
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _coerce_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value


# --- Eligibility -------------------------------------------------------------

class EligibilityRuleCreate(BaseModel):
    designation: str
    minimum_points: int = Field(0, ge=0)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    @field_validator("designation", mode="before")
    @classmethod
    def _validate_designation(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("designation cannot be empty")
        return value


class EligibilityRuleUpdate(BaseModel):
    designation: Optional[str] = None
    minimum_points: Optional[int] = Field(None, ge=0)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None


class EligibilityStatusUpdate(BaseModel):
    is_active: bool


class EligibilityRuleResponse(BaseModel):
    eligibility_rule_id: str
    code: Optional[str] = None
    designation: str
    minimum_points: int = 0
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _coerce_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value


# --- Summary -----------------------------------------------------------------

class AdminSummaryResponse(BaseModel):
    faculty_count: int
    active_faculty_count: int
    publication_count: int
    pending_verification_count: int
    academic_year_count: int
    current_academic_year: Optional[str] = None
    pending_registration_count: int = 0
