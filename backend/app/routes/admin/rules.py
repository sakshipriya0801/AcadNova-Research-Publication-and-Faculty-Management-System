"""Admin publication-rule routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin import (
    RuleAdminCreate,
    RuleAdminUpdate,
    RuleResponse,
    RuleStatusUpdate,
)
from app.services import rule_service
from app.utils.dates import to_iso_string

router = APIRouter(prefix="/api/admin/rules", tags=["admin: rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    admin: dict = Depends(dependencies.require_admin),
) -> list[RuleResponse]:
    rules = rule_service.list_rules()
    return [RuleResponse.model_validate(r) for r in rules]


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    admin: dict = Depends(dependencies.require_admin),
) -> RuleResponse:
    rule = rule_service.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return RuleResponse.model_validate(rule)


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: RuleAdminCreate,
    admin: dict = Depends(dependencies.require_admin),
) -> RuleResponse:
    _validate_effective_dates(request.effective_from, request.effective_to)
    rule = rule_service.create_rule(request.model_dump())
    _audit.log(admin, "create", "publication_rule", rule["rule_id"], new_value=rule)
    return RuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    request: RuleAdminUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> RuleResponse:
    data = request.model_dump(exclude_unset=True)
    _validate_effective_dates(data.get("effective_from"), data.get("effective_to"))
    rule = rule_service.update_rule(rule_id, data)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    _audit.log(admin, "update", "publication_rule", rule_id, new_value=rule)
    return RuleResponse.model_validate(rule)


@router.patch("/{rule_id}/status", response_model=RuleResponse)
async def update_rule_status(
    rule_id: str,
    request: RuleStatusUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> RuleResponse:
    rule = rule_service.update_rule(rule_id, {"is_active": request.is_active})
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    _audit.log(
        admin,
        "status",
        "publication_rule",
        rule_id,
        new_value={"is_active": request.is_active},
    )
    return RuleResponse.model_validate(rule)


def _validate_effective_dates(effective_from, effective_to) -> None:
    if effective_from is not None and effective_to is not None:
        if to_iso_string(effective_from) >= to_iso_string(effective_to):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "effective_from must be before effective_to",
            )
