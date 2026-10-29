"""Development helper to create or update an initial admin user.

Usage (from the ``backend/`` directory):

    ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='StrongPass123' \\
        python -m scripts.create_admin

If ``ADMIN_EMAIL`` / ``ADMIN_PASSWORD`` are not set, they are prompted for
securely.  The password is hashed before storage and is never printed.

This script intentionally does NOT create admins automatically on startup.
"""

import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Allow running as `python scripts/create_admin.py` and `python -m scripts.create_admin`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import mongodb  # noqa: E402
from app.models.collections import USERS  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


def _validate_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(char.isalpha() for char in password)
        and any(char.isdigit() for char in password)
    )


def main() -> None:
    email = (os.environ.get("ADMIN_EMAIL") or input("Admin email: ")).strip()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")

    if not email or not password:
        print("Email and password are required.", file=sys.stderr)
        sys.exit(1)

    if not _validate_password(password):
        print(
            "Password must be at least 8 characters and contain at least one "
            "letter and one number.",
            file=sys.stderr,
        )
        sys.exit(1)

    mongodb.init_mongodb()
    try:
        users = mongodb.get_collection(USERS)
        existing = users.find_one({"email": email, "role": UserRole.ADMIN.value})

        now = datetime.now(timezone.utc)
        password_hash = hash_password(password)

        if existing:
            users.update_one(
                {"email": email, "role": UserRole.ADMIN.value},
                {
                    "$set": {
                        "password_hash": password_hash,
                        "is_active": True,
                        "updated_at": now,
                    }
                },
            )
            print(f"Admin user '{email}' updated.")
        else:
            users.insert_one(
                {
                    "user_id": str(uuid4()),
                    "email": email,
                    "password_hash": password_hash,
                    "role": UserRole.ADMIN.value,
                    "faculty_id": None,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            print(f"Admin user '{email}' created.")
    finally:
        mongodb.close_mongodb()


if __name__ == "__main__":
    main()
