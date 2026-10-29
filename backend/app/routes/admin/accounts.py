"""Administrator account management routes (admin-only).

Only an authenticated administrator may list or create administrator accounts.
The role check is enforced server-side by ``require_admin``.
"""

from fastapi import APIRouter, Depends, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin_account import (
    AdminAccountListResponse,
    AdminAccountResponse,
    AdminCreateRequest,
)
from app.services import admin_account_service

router = APIRouter(prefix="/api/admin/accounts", tags=["admin: accounts"])


def _to_response(user: dict) -> AdminAccountResponse:
    return AdminAccountResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user.get("name"),
        is_active=user.get("is_active", True),
        created_at=user.get("created_at"),
    )


@router.get("", response_model=AdminAccountListResponse)
async def list_admin_accounts(
    admin: dict = Depends(dependencies.require_admin),
) -> AdminAccountListResponse:
    users = admin_account_service.list_admins()
    return AdminAccountListResponse(
        items=[_to_response(user) for user in users],
        total=len(users),
    )


@router.post(
    "",
    response_model=AdminAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_account(
    request: AdminCreateRequest,
    admin: dict = Depends(dependencies.require_admin),
) -> AdminAccountResponse:
    user = admin_account_service.create_admin(
        email=request.email,
        password=request.password,
        name=request.name,
    )
    # Audit without storing any credential material.
    _audit.log(
        admin,
        "create",
        "admin_account",
        user["user_id"],
        new_value={"email": user["email"], "name": user.get("name")},
    )
    return _to_response(user)
