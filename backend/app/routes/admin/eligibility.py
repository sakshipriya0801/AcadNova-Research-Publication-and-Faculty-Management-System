"""Admin eligibility-rule routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.admin import (
    EligibilityRuleCreate,
    EligibilityRuleResponse,
    EligibilityRuleUpdate,
    EligibilityStatusUpdate,
)
from app.services import rule_service
from app.utils.dates import to_iso_string

router = APIRouter(prefix="/api/admin/eligibility-rules", tags=["admin: eligibility"])


@router.get("", response_model=list[EligibilityRuleResponse])
async def list_eligibility_rules(
    admin: dict = Depends(dependencies.require_admin),
) -> list[EligibilityRuleResponse]:
    rules = rule_service.list_eligibility_rules(active_only=False)
    return [EligibilityRuleResponse.model_validate(r) for r in rules]


@router.post("", response_model=EligibilityRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_eligibility_rule(
    request: EligibilityRuleCreate,
    admin: dict = Depends(dependencies.require_admin),
) -> EligibilityRuleResponse:
    _validate_effective_dates(request.effective_from, request.effective_to)
    rule = rule_service.create_eligibility_rule(request.model_dump())
    _audit.log(
        admin, "create", "eligibility_rule", rule["eligibility_rule_id"], new_value=rule
    )
    return EligibilityRuleResponse.model_validate(rule)


@router.put("/{eligibility_rule_id}", response_model=EligibilityRuleResponse)
async def update_eligibility_rule(
    eligibility_rule_id: str,
    request: EligibilityRuleUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> EligibilityRuleResponse:
    data = request.model_dump(exclude_unset=True)
    _validate_effective_dates(data.get("effective_from"), data.get("effective_to"))
    rule = rule_service.update_eligibility_rule(eligibility_rule_id, data)
    _audit.log(
        admin,
        "update",
        "eligibility_rule",
        eligibility_rule_id,
        new_value=rule,
    )
    return EligibilityRuleResponse.model_validate(rule)


@router.patch("/{eligibility_rule_id}/status", response_model=EligibilityRuleResponse)
async def update_eligibility_rule_status(
    eligibility_rule_id: str,
    request: EligibilityStatusUpdate,
    admin: dict = Depends(dependencies.require_admin),
) -> EligibilityRuleResponse:
    rule = rule_service.set_eligibility_rule_status(
        eligibility_rule_id, request.is_active
    )
    _audit.log(
        admin,
        "status",
        "eligibility_rule",
        eligibility_rule_id,
        new_value={"is_active": request.is_active},
    )
    return EligibilityRuleResponse.model_validate(rule)


def _validate_effective_dates(effective_from, effective_to) -> None:
    if effective_from is not None and effective_to is not None:
        if to_iso_string(effective_from) >= to_iso_string(effective_to):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "effective_from must be before effective_to",
            )
