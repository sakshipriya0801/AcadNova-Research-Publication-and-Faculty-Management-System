"""Authentication request/response schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import DEPARTMENT_PROGRAMS, DESIGNATIONS


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    employee_id: Optional[str] = None
    department_id: str
    designation: str

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be empty")
        return cleaned

    @field_validator("employee_id")
    @classmethod
    def _clean_employee_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

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
    def _validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: EmailStr) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class CurrentUserResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    faculty_id: Optional[str] = None
    approval_status: Optional[str] = None
    must_change_password: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")
        return value
