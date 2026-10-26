"""
VaultGuard - Entities API Router (Customers, Merchants, Cases)
"""

from typing import List, Optional
import json
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.app.database import get_db
from backend.app.models.orm import (
    CustomerORM,
    MerchantORM,
    CaseORM,
    CaseHistoryORM,
    CaseNoteORM,
    FraudAlertORM,
    TransactionORM,
)
from backend.app.schemas.pydantic_schemas import (
    CustomerResponse,
    MerchantResponse,
    CaseResponse,
    CaseQueueResponse,
    CaseStatusUpdate,
    CaseCreate,
    CaseNoteCreate,
    CaseNoteResponse,
    CaseHistoryResponse,
    FraudAlertQueueItem,
)

router = APIRouter(prefix="/api", tags=["Entities"])


def _actor_name(x_analyst: Optional[str]) -> str:
    """Use a supplied analyst display name until authenticated identity is available."""
    return (x_analyst or "system").strip()[:128] or "system"


@router.get("/customers", response_model=List[CustomerResponse])
def get_customers(
    risk_level: Optional[str] = None,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated customer profiles with risk levels.
    """
    query = db.query(CustomerORM)
    if risk_level:
        query = query.filter(CustomerORM.risk_level == risk_level)
    if segment:
        query = query.filter(CustomerORM.segment == segment)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(CustomerORM.customer_id.ilike(search_filter))

    offset = (page - 1) * limit
    return query.order_by(CustomerORM.id.asc()).offset(offset).limit(limit).all()


@router.get("/merchants", response_model=List[MerchantResponse])
def get_merchants(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated merchant risk profiles and volume spike ratios.
    """
    query = db.query(MerchantORM)
    if category:
        query = query.filter(MerchantORM.category == category)
    if risk_level:
        query = query.filter(MerchantORM.risk_level == risk_level)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(MerchantORM.merchant_id.ilike(search_filter))

    offset = (page - 1) * limit
    return query.order_by(MerchantORM.spike_ratio.desc()).offset(offset).limit(limit).all()


@router.get("/cases", response_model=List[CaseResponse])
def get_cases(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves investigation cases created for high-risk micro-fraud incidents.
    """
    query = db.query(CaseORM)
    if status:
        query = query.filter(CaseORM.status == status)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                CaseORM.case_id.ilike(search_filter),
                CaseORM.customer_id.ilike(search_filter),
                CaseORM.title.ilike(search_filter),
            )
        )

    offset = (page - 1) * limit
    return query.order_by(CaseORM.id.desc()).offset(offset).limit(limit).all()


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    x_analyst: Optional[str] = Header(None, alias="X-Analyst"),
    db: Session = Depends(get_db),
):
    """Create one investigation case for a persisted suspicious transaction."""
    transaction = db.query(TransactionORM).filter(
        TransactionORM.transaction_id == payload.transaction_id
    ).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    existing = db.query(CaseORM).filter(CaseORM.transaction_id == payload.transaction_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Transaction already has case {existing.case_id}.")

    actor = _actor_name(x_analyst)
    customer_id = transaction.sender_id or transaction.customer_id or transaction.card_id or "Unknown"
    case = CaseORM(
        case_id=f"CASE-{uuid.uuid4().hex[:10].upper()}",
        title=payload.title or f"Investigation for {payload.transaction_id}",
        customer_id=customer_id,
        transaction_id=payload.transaction_id,
        risk_score=transaction.risk_score or 0.0,
        severity=payload.severity,
        status="Open",
        assigned_analyst=payload.assigned_analyst,
    )
    try:
        db.add(case)
        db.flush()
        db.add(CaseHistoryORM(case_id=case.case_id, event_type="created", new_status="Open", actor=actor))
        db.commit()
        db.refresh(case)
    except IntegrityError as exc:
        db.rollback()
        existing = db.query(CaseORM).filter(CaseORM.transaction_id == payload.transaction_id).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Transaction already has case {existing.case_id}.",
            ) from exc
        raise HTTPException(status_code=500, detail="Unable to create investigation case.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create investigation case.") from exc
    return case


@router.get("/cases/{case_id}/notes", response_model=List[CaseNoteResponse])
def get_case_notes(case_id: str, db: Session = Depends(get_db)):
    if not db.query(CaseORM.id).filter(CaseORM.case_id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found.")
    return db.query(CaseNoteORM).filter(CaseNoteORM.case_id == case_id).order_by(CaseNoteORM.created_at.desc()).all()


@router.post("/cases/{case_id}/notes", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
def add_case_note(
    case_id: str,
    payload: CaseNoteCreate,
    x_analyst: Optional[str] = Header(None, alias="X-Analyst"),
    db: Session = Depends(get_db),
):
    if not db.query(CaseORM.id).filter(CaseORM.case_id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found.")
    note = CaseNoteORM(case_id=case_id, note=payload.note, author=_actor_name(x_analyst))
    try:
        db.add(note)
        db.add(CaseHistoryORM(case_id=case_id, event_type="note_added", actor=note.author, detail="Investigation note added"))
        db.commit()
        db.refresh(note)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to save investigation note.") from exc
    return note


@router.get("/cases/{case_id}/history", response_model=List[CaseHistoryResponse])
def get_case_history(case_id: str, db: Session = Depends(get_db)):
    if not db.query(CaseORM.id).filter(CaseORM.case_id == case_id).first():
        raise HTTPException(status_code=404, detail="Case not found.")
    return db.query(CaseHistoryORM).filter(CaseHistoryORM.case_id == case_id).order_by(CaseHistoryORM.created_at.desc()).all()


@router.get("/cases/active", response_model=CaseQueueResponse)
def get_active_case_queue(
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Returns active investigation cases and fraud alerts with transaction context."""
    closed_case_statuses = ["False Positive", "Confirmed Fraud", "Resolved"]
    case_query = db.query(CaseORM).filter(~CaseORM.status.in_(closed_case_statuses))
    alert_query = (
        db.query(FraudAlertORM, TransactionORM)
        .outerjoin(
            TransactionORM,
            TransactionORM.transaction_id == FraudAlertORM.transaction_id,
        )
        .filter(
            func.upper(FraudAlertORM.review_status).notin_(
                [
                    "FALSE POSITIVE",
                    "FALSE_POSITIVE",
                    "CONFIRMED FRAUD",
                    "CONFIRMED_FRAUD",
                    "RESOLVED",
                    "DISMISSED",
                ]
            )
        )
    )

    if search:
        search_filter = f"%{search}%"
        case_query = case_query.filter(
            or_(CaseORM.case_id.ilike(search_filter),
                CaseORM.customer_id.ilike(search_filter),
                CaseORM.title.ilike(search_filter))
        )
        alert_query = alert_query.filter(
            or_(FraudAlertORM.alert_id.ilike(search_filter),
                FraudAlertORM.transaction_id.ilike(search_filter),
                TransactionORM.sender_id.ilike(search_filter),
                TransactionORM.sender_vpa.ilike(search_filter))
        )

    cases = case_query.order_by(CaseORM.id.desc()).limit(limit).all()
    alert_rows = alert_query.order_by(FraudAlertORM.created_at.desc()).limit(limit).all()

    alerts = []
    for alert, transaction in alert_rows:
        try:
            reasons = json.loads(alert.reasons or "[]")
            if not isinstance(reasons, list):
                reasons = [str(reasons)]
        except (TypeError, ValueError):
            reasons = [alert.reasons] if alert.reasons else []

        alerts.append(
            FraudAlertQueueItem(
                id=alert.id,
                alert_id=alert.alert_id,
                transaction_id=alert.transaction_id,
                risk_score=alert.risk_score,
                risk_category=alert.risk_category,
                reasons=reasons,
                status=alert.review_status,
                analyst=alert.analyst,
                created_at=alert.created_at,
                amount_inr=transaction.amount_inr if transaction else None,
                channel=transaction.channel if transaction else None,
                timestamp=transaction.timestamp if transaction else None,
                decision=transaction.decision if transaction else None,
            )
        )

    return CaseQueueResponse(cases=cases, alerts=alerts)


@router.patch("/cases/{case_id}/status", response_model=CaseResponse)
def update_case_status(
    case_id: str,
    status_update: CaseStatusUpdate,
    x_analyst: Optional[str] = Header(None, alias="X-Analyst"),
    db: Session = Depends(get_db),
):
    """Updates a case outcome and commits it to the configured database."""
    case = db.query(CaseORM).filter(CaseORM.case_id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    previous_status = case.status
    case.status = status_update.status
    if status_update.status in {"Confirmed Fraud", "False Positive", "Resolved"}:
        case.outcome = status_update.status
        case.closure_reason = status_update.closure_reason
    try:
        # Test doubles that intentionally fail commits may expose only query/commit;
        # production SQLAlchemy sessions always support add and keep this audit row atomic.
        if hasattr(db, "add"):
            db.add(CaseHistoryORM(
                case_id=case.case_id, event_type="status_changed", previous_status=previous_status,
                new_status=case.status, actor=_actor_name(x_analyst), detail=status_update.closure_reason,
            ))
        db.commit()
        db.refresh(case)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update case status.",
        ) from exc
    return case


@router.patch("/fraud-alerts/{alert_id}/status", response_model=FraudAlertQueueItem)
def update_fraud_alert_status(
    alert_id: int,
    status_update: CaseStatusUpdate,
    db: Session = Depends(get_db),
):
    """Updates a persisted fraud-alert review outcome and returns transaction context."""
    row = (
        db.query(FraudAlertORM, TransactionORM)
        .outerjoin(
            TransactionORM,
            TransactionORM.transaction_id == FraudAlertORM.transaction_id,
        )
        .filter(FraudAlertORM.id == alert_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fraud alert not found.")

    alert, transaction = row
    alert.review_status = status_update.status.upper().replace(" ", "_")
    try:
        db.commit()
        db.refresh(alert)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update fraud-alert status.",
        ) from exc

    try:
        reasons = json.loads(alert.reasons or "[]")
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
    except (TypeError, ValueError):
        reasons = [alert.reasons] if alert.reasons else []

    return FraudAlertQueueItem(
        id=alert.id,
        alert_id=alert.alert_id,
        transaction_id=alert.transaction_id,
        risk_score=alert.risk_score,
        risk_category=alert.risk_category,
        reasons=reasons,
        status=alert.review_status,
        analyst=alert.analyst,
        created_at=alert.created_at,
        amount_inr=transaction.amount_inr if transaction else None,
        channel=transaction.channel if transaction else None,
        timestamp=transaction.timestamp if transaction else None,
        decision=transaction.decision if transaction else None,
    )
