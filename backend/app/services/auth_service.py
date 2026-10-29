"""Authentication and registration business logic."""

import secrets
import string
from typing import Optional, Tuple

from fastapi import HTTPException, status

from app.config.settings import get_settings
from app.schemas.auth import RegisterRequest
from app.services import faculty_service, user_service
from app.utils import security


def generate_temp_password() -> str:
    """Generate a cryptographically random 5-character temporary password.

    Uses ``secrets`` (never ``random``/``Math.random``).  The result always
    contains at least one letter and one digit so it is never all digits.
    """
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(5))
        if any(char.isalpha() for char in password) and any(char.isdigit() for char in password):
            return password


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Return the user document when credentials are valid, else None.

    The same None is returned for "unknown email" and "wrong password" so the
    caller can produce a generic error that does not reveal account existence.
    """
    user = user_service.find_user_by_email(email)
    if user is None:
        return None
    if not security.verify_password(password, user.get("password_hash", "")):
        return None
    return user


def register_faculty(request: RegisterRequest) -> dict:
    """Register a faculty member and its linked user (role is always faculty).

    Newly self-registered faculty are ``pending`` administrator approval unless
    the deployment disables approval (see ``require_registration_approval``).

    Raises HTTPException(409) on duplicate email or employee id.
    """
    approval = (
        "pending" if get_settings().require_registration_approval else "approved"
    )
    return _create_faculty(
        name=request.name,
        email=request.email,
        password=request.password,
        employee_id=request.employee_id,
        department_id=request.department_id,
        designation=request.designation,
        approval_status=approval,
    )


def create_faculty_account(
    name: str,
    email: str,
    password: Optional[str],
    employee_id: Optional[str] = None,
    department_id: Optional[str] = None,
    designation: Optional[str] = None,
) -> Tuple[dict, Optional[str]]:
    """Create a faculty account via the administrator console (pre-approved).

    If ``password`` is omitted/blank, a random temporary password is generated
    and returned (once).  Returns ``(user, generated_password)``; the generated
    password is ``None`` when the caller supplied an explicit password.
    """
    generated_password = None
    if not password:
        generated_password = generate_temp_password()
        password = generated_password

    user = _create_faculty(
        name=name,
        email=email,
        password=password,
        employee_id=employee_id,
        department_id=department_id,
        designation=designation,
        approval_status="approved",
        must_change_password=True,
    )
    return user, generated_password


def _create_faculty(
    name: str,
    email: str,
    password: str,
    employee_id: Optional[str],
    department_id: Optional[str],
    designation: Optional[str],
    approval_status: str,
    must_change_password: bool = False,
) -> dict:
    if user_service.find_user_by_email(email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    if employee_id and (
        faculty_service.find_faculty_by_employee_id(employee_id) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID already registered",
        )

    faculty = faculty_service.create_faculty(
        {
            "name": name,
            "email": email,
            "employee_id": employee_id,
            "department_id": department_id,
            "designation": designation,
        }
    )

    return user_service.create_user(
        {
            "email": email,
            "password_hash": security.hash_password(password),
            "role": "faculty",
            "faculty_id": faculty["faculty_id"],
            "is_active": True,
            "approval_status": approval_status,
            "must_change_password": must_change_password,
        }
    )


def change_password(user: dict, new_password: str) -> dict:
    """Set a new password for the user and clear the must-change flag.

    Raises 400 if the new password equals the current one.  The plaintext
    password is hashed and never stored or logged.
    """
    if security.verify_password(new_password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password",
        )
    user_service.update_user(
        user["user_id"],
        {
            "password_hash": security.hash_password(new_password),
            "must_change_password": False,
        },
    )
    return user_service.find_user_by_id(user["user_id"])
