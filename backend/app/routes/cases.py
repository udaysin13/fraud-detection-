"""Investigation cases and fraud-alert workflow endpoints."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.orm import (
    CaseORM,
    CaseNoteORM,
    CaseHistoryORM,
    FraudAlertORM,
    TransactionORM,
)
from backend.app.schemas.pydantic_schemas import (
    CaseCreate,
    CaseResponse,
    CaseStatusUpdate,
    CaseNoteCreate,
    CaseNoteResponse,
    CaseHistoryResponse,
    CaseQueueItem,
    FraudAlertQueueItem,
    CaseQueueResponse,
)

router = APIRouter(prefix="/api", tags=["Investigations"])


def _case_history(db: Session, case_id: str, event_type: str,
                  previous_status: Optional[str], new_status: Optional[str],
                  detail: Optional[str] = None) -> None:
    db.add(CaseHistoryORM(
        case_id=case_id,
        event_type=event_type,
        previous_status=previous_status,
        new_status=new_status,
        actor="analyst",
        detail=detail,
    ))


def _alert_status_label(status_value: Optional[str]) -> str:
    value = (status_value or "OPEN").strip().upper().replace(" ", "_")
    return {
        "OPEN": "Open",
        "UNDER_REVIEW": "Under Review",
        "RESOLVED": "Resolved",
        "DISMISSED": "False Positive",
    }.get(value, value.replace("_", " ").title())


@router.get("/cases", response_model=list[CaseResponse])
def get_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(CaseORM)
    if status_filter and status_filter != "All":
        query = query.filter(CaseORM.status == status_filter)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(CaseORM.case_id.ilike(pattern),
                                 CaseORM.title.ilike(pattern),
                                 CaseORM.customer_id.ilike(pattern),
                                 CaseORM.transaction_id.ilike(pattern)))
    return query.order_by(CaseORM.id.desc()).offset((page - 1) * limit).limit(limit).all()


@router.get("/cases/active", response_model=CaseQueueResponse)
def get_active_case_queue(
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    case_query = db.query(CaseORM).filter(CaseORM.status.notin_(["Resolved", "False Positive"]))
    if search:
        pattern = f"%{search}%"
        case_query = case_query.filter(or_(CaseORM.case_id.ilike(pattern),
                                           CaseORM.title.ilike(pattern),
                                           CaseORM.customer_id.ilike(pattern)))
    cases = case_query.order_by(CaseORM.id.desc()).limit(limit).all()

    alert_query = db.query(FraudAlertORM).filter(
        FraudAlertORM.review_status.notin_(["RESOLVED", "DISMISSED"])
    )
    if search:
        pattern = f"%{search}%"
        alert_query = alert_query.filter(or_(FraudAlertORM.alert_id.ilike(pattern),
                                             FraudAlertORM.transaction_id.ilike(pattern),
                                             FraudAlertORM.risk_category.ilike(pattern)))
    alerts = alert_query.order_by(FraudAlertORM.id.desc()).limit(limit).all()
    transaction_ids = [alert.transaction_id for alert in alerts]
    transactions = {}
    if transaction_ids:
        for txn in db.query(TransactionORM).filter(TransactionORM.transaction_id.in_(transaction_ids)).all():
            transactions[txn.transaction_id] = txn

    alert_items = []
    for alert in alerts:
        txn = transactions.get(alert.transaction_id)
        try:
            reasons = json.loads(alert.reasons or "[]")
            if not isinstance(reasons, list):
                reasons = [str(reasons)]
        except (TypeError, ValueError):
            reasons = [str(alert.reasons)] if alert.reasons else []
        alert_items.append(FraudAlertQueueItem(
            id=alert.id,
            alert_id=alert.alert_id,
            transaction_id=alert.transaction_id,
            risk_score=alert.risk_score,
            risk_category=alert.risk_category,
            reasons=reasons,
            status=_alert_status_label(alert.review_status),
            analyst=alert.analyst,
            created_at=alert.created_at,
            amount_inr=(txn.amount_inr if txn else None),
            channel=(txn.channel if txn else None),
            timestamp=(txn.timestamp if txn else None),
            decision=(txn.decision if txn else None),
        ))
    return CaseQueueResponse(
        cases=[CaseQueueItem.model_validate(case) for case in cases],
        alerts=alert_items,
    )


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    txn = db.query(TransactionORM).filter(
        TransactionORM.transaction_id == payload.transaction_id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    existing = db.query(CaseORM).filter(
        CaseORM.transaction_id == payload.transaction_id
    ).first()
    if existing:
        return existing
    case = CaseORM(
        case_id=f"CASE-{uuid.uuid4().hex[:10].upper()}",
        title=payload.title or f"Investigation for {payload.transaction_id}",
        customer_id=txn.customer_id or txn.sender_id or "Unknown",
        risk_score=float(txn.risk_score or 0),
        status="Open",
        assigned_analyst=payload.assigned_analyst,
        transaction_id=payload.transaction_id,
        severity=payload.severity,
    )
    db.add(case)
    db.flush()
    _case_history(db, case.case_id, "created", None, case.status,
                  f"Created for transaction {payload.transaction_id}")
    db.commit()
    db.refresh(case)
    return case


@router.patch("/cases/{case_id}/status", response_model=CaseResponse)
def update_case_status(case_id: str, payload: CaseStatusUpdate, db: Session = Depends(get_db)):
    case = db.query(CaseORM).filter(CaseORM.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    previous = case.status
    case.status = payload.status
    if payload.closure_reason is not None:
        case.closure_reason = payload.closure_reason
    if payload.status in ("Resolved", "False Positive", "Confirmed Fraud"):
        case.outcome = payload.status
    _case_history(db, case.case_id, "status_changed", previous, case.status,
                  payload.closure_reason)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases/{case_id}/notes", response_model=list[CaseNoteResponse])
def get_case_notes(case_id: str, db: Session = Depends(get_db)):
    if not db.query(CaseORM).filter(CaseORM.case_id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found.")
    return db.query(CaseNoteORM).filter(CaseNoteORM.case_id == case_id).order_by(CaseNoteORM.id.asc()).all()


@router.post("/cases/{case_id}/notes", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
def add_case_note(case_id: str, payload: CaseNoteCreate, db: Session = Depends(get_db)):
    if not db.query(CaseORM).filter(CaseORM.case_id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found.")
    note = CaseNoteORM(case_id=case_id, note=payload.note.strip(), author="analyst")
    db.add(note)
    db.add(CaseHistoryORM(case_id=case_id, event_type="note_added", actor="analyst",
                          detail=payload.note.strip()))
    db.commit()
    db.refresh(note)
    return note


@router.get("/cases/{case_id}/history", response_model=list[CaseHistoryResponse])
def get_case_history(case_id: str, db: Session = Depends(get_db)):
    if not db.query(CaseORM).filter(CaseORM.case_id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found.")
    return db.query(CaseHistoryORM).filter(CaseHistoryORM.case_id == case_id).order_by(CaseHistoryORM.id.desc()).all()


@router.patch("/fraud-alerts/{alert_id}/status")
def update_fraud_alert_status(alert_id: str, payload: dict, db: Session = Depends(get_db)):
    alert = db.query(FraudAlertORM).filter(FraudAlertORM.id == alert_id).first()
    if not alert:
        alert = db.query(FraudAlertORM).filter(FraudAlertORM.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Fraud alert not found.")
    requested = str(payload.get("status", "")).strip().lower().replace("_", " ")
    status_map = {
        "open": "OPEN",
        "under review": "UNDER_REVIEW",
        "in review": "UNDER_REVIEW",
        "escalated": "UNDER_REVIEW",
        "false positive": "DISMISSED",
        "dismissed": "DISMISSED",
        "confirmed fraud": "RESOLVED",
        "resolved": "RESOLVED",
    }
    if requested not in status_map:
        raise HTTPException(status_code=422, detail="Unsupported fraud-alert status.")
    alert.review_status = status_map[requested]
    alert.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return {
        "id": alert.id,
        "alert_id": alert.alert_id,
        "transaction_id": alert.transaction_id,
        "risk_score": alert.risk_score,
        "risk_category": alert.risk_category,
        "status": _alert_status_label(alert.review_status),
        "analyst": alert.analyst,
    }
