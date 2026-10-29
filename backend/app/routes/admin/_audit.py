"""Shared helper for audit logging in admin routes."""

from app.services import audit_service


def log(
    user: dict,
    action: str,
    entity_type: str,
    entity_id: str = None,
    old_value: dict = None,
    new_value: dict = None,
) -> None:
    audit_service.log_audit(
        user_id=user.get("user_id"),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
    )
