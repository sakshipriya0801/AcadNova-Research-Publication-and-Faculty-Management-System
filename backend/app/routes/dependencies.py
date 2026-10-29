"""Reusable authentication and authorization dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

from app.services import user_service
from app.utils import security

_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_authenticated_user_basic(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Validate the token and return the user (inactive/approval checks only).

    Used by the minimum endpoints that a faculty member must reach even while
    they are required to change their password (e.g. ``/api/auth/me`` and the
    password-change endpoint).
    """
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated")

    try:
        payload = security.decode_access_token(credentials.credentials)
    except PyJWTError:
        raise _unauthorized("Invalid or expired token")

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise _unauthorized("Invalid token payload")

    user = user_service.find_user_by_id(user_id)
    if user is None:
        raise _unauthorized("User not found")
    if not user.get("is_active", False):
        raise _unauthorized("Inactive user")
    if user.get("role") == "faculty" and user_service.approval_status(user) != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not approved",
        )

    return user


def require_authenticated_user(
    user: dict = Depends(require_authenticated_user_basic),
) -> dict:
    """Full-access dependency: additionally blocks faculty who must change
    their password until they do so."""
    if user.get("role") == "faculty" and user_service.must_change_password(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
        )
    return user


def require_faculty(user: dict = Depends(require_authenticated_user)) -> dict:
    """Require an authenticated user with the faculty role."""
    if user.get("role") != "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty role required",
        )
    return user


def require_admin(user: dict = Depends(require_authenticated_user)) -> dict:
    """Require an authenticated user with the admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
