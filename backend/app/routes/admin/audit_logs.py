"""Admin audit-log listing route (read-only).

Exposes recorded administrative actions for the admin console.  Authorization
is enforced server-side by ``require_admin``; faculty receive 403.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.routes import dependencies
from app.schemas.admin_audit import AuditLogListResponse, AuditLogResponse
from app.services import audit_service

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin: audit logs"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    admin: dict = Depends(dependencies.require_admin),
) -> AuditLogListResponse:
    result = audit_service.list_audit_logs(
        page=page,
        page_size=page_size,
        action=action,
        entity_type=entity_type,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse(**item) for item in result["items"]],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        total_pages=result["total_pages"],
    )
