"""Controlled configuration for transparent risk rules."""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import get_db
from backend.app.models.orm import RuleConfigORM, RuleHistoryORM
from backend.app.schemas.pydantic_schemas import RuleConfigResponse, RuleConfigUpdate, RuleHistoryResponse
from backend.app.services.risk_rules import DEFAULT_RULE_CONFIGURATION, get_rule_configuration

router = APIRouter(prefix="/api/rules", tags=["Risk Rules"])


def _require_admin_token(token: Optional[str]) -> None:
    required = os.getenv("VAULTGUARD_ADMIN_TOKEN")
    if not required:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rule editing is disabled until VAULTGUARD_ADMIN_TOKEN is configured.",
        )
    if token != required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid administrative token required.")


def _validate_rule_value(rule_key: str, value: float) -> float:
    if rule_key not in DEFAULT_RULE_CONFIGURATION:
        raise HTTPException(status_code=404, detail="Unknown or unsupported risk-rule setting.")
    if rule_key in {"rapid_window_minutes", "rapid_transaction_count"} and value < 1:
        raise HTTPException(status_code=422, detail=f"{rule_key} must be at least 1.")
    if rule_key == "rapid_transaction_count" and not value.is_integer():
        raise HTTPException(status_code=422, detail="rapid_transaction_count must be a whole number.")
    if rule_key.endswith("_enabled") and value not in {0, 1}:
        raise HTTPException(status_code=422, detail=f"{rule_key} must be 0 or 1.")
    if rule_key in {"amount_ratio_threshold", "amount_review_threshold"} and value <= 0:
        raise HTTPException(status_code=422, detail=f"{rule_key} must be greater than 0.")
    return value


@router.get("", response_model=list[RuleConfigResponse])
def list_rule_configs(db: Session = Depends(get_db)):
    """Return effective rules; values are safe to view but changes require an admin token."""
    effective = get_rule_configuration(db)
    persisted = {row.rule_key: row for row in db.query(RuleConfigORM).all()}
    return [
        RuleConfigResponse(
            rule_key=key,
            value=float(effective[key]),
            enabled=bool(persisted[key].enabled) if key in persisted else True,
            version=persisted[key].version if key in persisted else 0,
            updated_by=persisted[key].updated_by if key in persisted else "environment_default",
            updated_at=persisted[key].updated_at if key in persisted else None,
        )
        for key in DEFAULT_RULE_CONFIGURATION
    ]


@router.put("/{rule_key}", response_model=RuleConfigResponse)
def update_rule_config(
    rule_key: str,
    payload: RuleConfigUpdate,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    x_analyst: Optional[str] = Header(None, alias="X-Analyst"),
    db: Session = Depends(get_db),
):
    """Create or version an enabled/disabled threshold override after admin authorization."""
    _require_admin_token(x_admin_token)
    value = _validate_rule_value(rule_key, payload.value)
    actor = (x_analyst or "admin").strip()[:128] or "admin"
    rule = db.query(RuleConfigORM).filter(RuleConfigORM.rule_key == rule_key).first()
    previous_value = rule.value if rule else None
    previous_enabled = rule.enabled if rule else None
    if rule is None:
        rule = RuleConfigORM(rule_key=rule_key, value=value, enabled=int(payload.enabled), version=1, updated_by=actor)
        db.add(rule)
    else:
        rule.value = value
        rule.enabled = int(payload.enabled)
        rule.version += 1
        rule.updated_by = actor
        rule.updated_at = datetime.now(timezone.utc)
    try:
        db.flush()
        db.add(RuleHistoryORM(
            rule_key=rule_key, previous_value=previous_value, new_value=value,
            previous_enabled=previous_enabled, new_enabled=int(payload.enabled),
            version=rule.version, changed_by=actor,
        ))
        db.commit()
        db.refresh(rule)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update risk-rule configuration.") from exc
    return rule


@router.get("/{rule_key}/history", response_model=list[RuleHistoryResponse])
def get_rule_history(rule_key: str, db: Session = Depends(get_db)):
    if rule_key not in DEFAULT_RULE_CONFIGURATION:
        raise HTTPException(status_code=404, detail="Unknown risk-rule setting.")
    return db.query(RuleHistoryORM).filter(RuleHistoryORM.rule_key == rule_key).order_by(RuleHistoryORM.created_at.desc()).all()
