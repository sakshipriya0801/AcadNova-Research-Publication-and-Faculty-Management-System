"""Password hashing and JWT token helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.config.settings import get_settings

_password_hasher = PasswordHash((BcryptHasher(),))


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when the plain password matches the stored hash."""
    try:
        return _password_hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    user_id: str,
    faculty_id: Optional[str],
    role: str,
) -> str:
    """Create a signed JWT with user identity, role and expiration."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "user_id": user_id,
        "faculty_id": faculty_id,
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising jwt.PyJWTError on failure."""
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
