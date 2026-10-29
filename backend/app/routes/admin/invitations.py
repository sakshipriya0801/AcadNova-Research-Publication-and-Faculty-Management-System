"""Administrator invitation routes (admin-only).

Only authenticated administrators may create, list or revoke invitations.
Tokens are never logged and are only returned once, at creation time.
"""

from fastapi import APIRouter, Depends, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin_invitation import (
    AdminInvitationCreateRequest,
    AdminInvitationCreateResponse,
    AdminInvitationListResponse,
    AdminInvitationResponse,
)
from app.services import admin_invitation_service

router = APIRouter(prefix="/api/admin/invitations", tags=["admin: invitations"])


@router.get("", response_model=AdminInvitationListResponse)
async def list_invitations(
    admin: dict = Depends(dependencies.require_admin),
) -> AdminInvitationListResponse:
    invitations = admin_invitation_service.list_invitations()
    return AdminInvitationListResponse(
        items=[
            AdminInvitationResponse(**admin_invitation_service.to_response(item))
            for item in invitations
        ],
        total=len(invitations),
    )


@router.post(
    "",
    response_model=AdminInvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    request: AdminInvitationCreateRequest,
    admin: dict = Depends(dependencies.require_admin),
) -> AdminInvitationCreateResponse:
    document, token = admin_invitation_service.create_invitation(
        email=request.email,
        created_by_user_id=admin.get("user_id"),
        expires_in_hours=request.expires_in_hours,
    )
    # Audit without storing the token.
    _audit.log(
        admin,
        "create",
        "admin_invitation",
        document["invitation_id"],
        new_value={"email": document["email"], "expires_at": document["expires_at"]},
    )
    response = admin_invitation_service.to_response(document)
    return AdminInvitationCreateResponse(
        invitation_id=response["invitation_id"],
        email=response["email"],
        status=response["status"],
        expires_at=document["expires_at"],
        created_at=document["created_at"],
        token=token,
    )


@router.post(
    "/{invitation_id}/revoke",
    response_model=AdminInvitationResponse,
)
async def revoke_invitation(
    invitation_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> AdminInvitationResponse:
    document = admin_invitation_service.revoke_invitation(invitation_id)
    _audit.log(admin, "revoke", "admin_invitation", invitation_id)
    return AdminInvitationResponse(
        **admin_invitation_service.to_response(document)
    )
