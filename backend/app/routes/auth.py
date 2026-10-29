"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.schemas.admin_invitation import AdminRegisterRequest
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import (
    admin_account_service,
    admin_invitation_service,
    audit_service,
    auth_service,
    user_service,
)
from app.utils import security

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(request: RegisterRequest) -> CurrentUserResponse:
    user = auth_service.register_faculty(request)
    return CurrentUserResponse(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
        faculty_id=user.get("faculty_id"),
        approval_status=user_service.approval_status(user),
    )


@router.post(
    "/admin-register",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_register(request: AdminRegisterRequest) -> CurrentUserResponse:
    """Register an administrator using a valid, unexpired invitation.

    The invitation is validated and atomically consumed before the account is
    created; the role is always ``admin`` and can never be chosen by the client.
    """
    invitation = admin_invitation_service.validate_invitation(
        request.token, request.email
    )
    if user_service.find_user_by_email(request.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    admin_invitation_service.consume_invitation(invitation["invitation_id"])
    user = admin_account_service.create_admin(
        email=request.email,
        password=request.password,
        name=request.name,
    )
    audit_service.log_audit(
        None,
        "admin.register",
        "admin_account",
        user["user_id"],
        new_value={"email": user["email"]},
    )
    return CurrentUserResponse(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
        faculty_id=user.get("faculty_id"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    user = auth_service.authenticate_user(request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    approval = user_service.approval_status(user)
    if user.get("role") == "faculty" and approval != "approved":
        detail = (
            "Your account is pending administrator approval."
            if approval == "pending"
            else "Your account has been rejected."
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    token = security.create_access_token(
        user_id=user["user_id"],
        faculty_id=user.get("faculty_id"),
        role=user["role"],
    )
    return TokenResponse(
        access_token=token,
        must_change_password=user_service.must_change_password(user),
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    user: dict = Depends(dependencies.require_authenticated_user_basic),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
        faculty_id=user.get("faculty_id"),
        approval_status=user_service.approval_status(user),
        must_change_password=user_service.must_change_password(user),
    )


@router.post("/change-password", response_model=CurrentUserResponse)
async def change_password(
    request: ChangePasswordRequest,
    user: dict = Depends(dependencies.require_authenticated_user_basic),
) -> CurrentUserResponse:
    """Set a new password and clear the must-change flag.

    Only the authenticated user may change their own password.  The new
    password must differ from the current one and match the confirmation.
    """
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )
    updated = auth_service.change_password(user, request.new_password)
    audit_service.log_audit(
        user.get("user_id"),
        "password.change",
        "user",
        updated["user_id"],
        new_value={"must_change_password": False},
    )
    return CurrentUserResponse(
        user_id=updated["user_id"],
        email=updated["email"],
        role=updated["role"],
        faculty_id=updated.get("faculty_id"),
        approval_status=user_service.approval_status(updated),
        must_change_password=False,
    )


@router.get("/test")
async def protected_test(
    user: dict = Depends(dependencies.require_authenticated_user),
) -> dict:
    return {"message": "Authentication successful"}


@router.get("/admin-test")
async def admin_test(
    admin: dict = Depends(dependencies.require_admin),
) -> dict:
    return {"message": "Admin access granted"}
