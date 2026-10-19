"""
VaultGuard - Transactions & Real-Time Prediction Router

Handles:
- Paginated retrieval and multi-attribute filtering of transactions.
- Single transaction lookup by ID.
- Real-Time inference endpoint (/api/predict) with historical feature retrieval,
  deduplication safeguards, and automated alert generation.
"""

from datetime import datetime, timezone
import json
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.app.database import get_db
from backend.app.models.orm import TransactionORM, AlertORM, FraudAlertORM
from backend.app.schemas.pydantic_schemas import (
    TransactionResponse,
    TransactionDetailResponse,
    TransactionPredictRequest,
    PredictionResponse,
)
from backend.app.services.ml_service import predict_single_transaction

router = APIRouter(prefix="/api", tags=["Transactions & Scoring"])


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    decision: Optional[str] = None,
    risk_category: Optional[str] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated transactions with optional multi-attribute filtering.
    Supports both Indian payment attributes and legacy card attributes.
    """
    query = db.query(TransactionORM)

    if decision:
        query = query.filter(TransactionORM.decision == decision)
    if risk_category:
        query = query.filter(TransactionORM.risk_category == risk_category)
    if segment:
        query = query.filter(TransactionORM.segment == segment)
    if channel:
        query = query.filter(TransactionORM.channel == channel)
    if min_amount is not None:
        query = query.filter(
            or_(
                TransactionORM.amount >= min_amount,
                TransactionORM.amount_inr >= min_amount,
            )
        )
    if max_amount is not None:
        query = query.filter(
            or_(
                TransactionORM.amount <= max_amount,
                TransactionORM.amount_inr <= max_amount,
            )
        )

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                TransactionORM.transaction_id.ilike(search_filter),
                TransactionORM.sender_id.ilike(search_filter),
                TransactionORM.beneficiary_id.ilike(search_filter),
                TransactionORM.sender_vpa.ilike(search_filter),
                TransactionORM.beneficiary_vpa.ilike(search_filter),
                TransactionORM.card_id.ilike(search_filter),
                TransactionORM.customer_id.ilike(search_filter),
                TransactionORM.merchant_id.ilike(search_filter),
            )
        )

    offset = (page - 1) * limit
    results = query.order_by(desc(TransactionORM.id)).offset(offset).limit(limit).all()

    out = []
    for r in results:
        reasons_list = []
        if r.reasons:
            try:
                reasons_list = json.loads(r.reasons)
                if not isinstance(reasons_list, list):
                    reasons_list = [str(reasons_list)]
            except Exception:
                reasons_list = [str(r.reasons)]

        amt = r.amount if r.amount is not None else (r.amount_inr or 0.0)

        item = TransactionResponse(
            id=r.id,
            transaction_id=r.transaction_id,
            timestamp=r.timestamp or "",
            card_id=r.card_id or (r.sender_vpa or r.sender_id or ""),
            customer_id=r.customer_id or (r.sender_id or ""),
            merchant_id=r.merchant_id or (r.beneficiary_id or ""),
            merchant_category=r.merchant_category or "p2p_transfer",
            amount=amt,
            currency=r.currency or "INR",
            country=r.country or "IN",
            billing_country=r.billing_country or "IN",
            device_id=r.device_id or "",
            ip_address=r.ip_address or "",
            is_new_device=r.is_new_device or 0,
            bin_range=r.bin_range or "",
            channel=r.channel or "UPI_P2P",
            segment=r.segment or "UPI P2P",
            is_fraud=r.is_fraud or 0,
            risk_score=r.risk_score or 0.0,
            decision=r.decision or "Allow",
            risk_category=r.risk_category or "LOW_RISK",
            reasons=reasons_list,
            status=r.status or "Approved",
        )
        out.append(item)

    return out


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction_by_id(transaction_id: str, db: Session = Depends(get_db)):
    """Retrieves full details for a specific transaction."""
    r = db.query(TransactionORM).filter(TransactionORM.transaction_id == transaction_id).first()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    reasons_list = []
    if r.reasons:
        try:
            reasons_list = json.loads(r.reasons)
            if not isinstance(reasons_list, list):
                reasons_list = [str(reasons_list)]
        except Exception:
            reasons_list = [str(r.reasons)]

    amt = r.amount if r.amount is not None else (r.amount_inr or 0.0)

    return TransactionDetailResponse(
        id=r.id,
        transaction_id=r.transaction_id,
        timestamp=r.timestamp or "",
        card_id=r.card_id or "",
        customer_id=r.customer_id or "",
        merchant_id=r.merchant_id or "",
        merchant_category=r.merchant_category or "",
        amount=amt,
        currency=r.currency or "INR",
        country=r.country or "IN",
        billing_country=r.billing_country or "IN",
        device_id=r.device_id or "",
        ip_address=r.ip_address or "",
        is_new_device=r.is_new_device or 0,
        bin_range=r.bin_range or "",
        channel=r.channel or "UPI_P2P",
        segment=r.segment or "",
        is_fraud=r.is_fraud or 0,
        risk_score=r.risk_score or 0.0,
        decision=r.decision or "Allow",
        risk_category=r.risk_category or "LOW_RISK",
        reasons=reasons_list,
        status=r.status or "Approved",
        amount_inr=r.amount_inr,
        transaction_type=r.transaction_type,
        sender_id=r.sender_id,
        beneficiary_id=r.beneficiary_id,
        sender_vpa=r.sender_vpa,
        beneficiary_vpa=r.beneficiary_vpa,
        sim_change_flag=r.sim_change_flag,
        ip_location_state=r.ip_location_state,
        model_version=r.model_version,
        scored_at=r.scored_at,
        source=r.source,
    )


@router.post("/predict", response_model=PredictionResponse)
def score_single_transaction_api(
    payload: TransactionPredictRequest, db: Session = Depends(get_db)
):
    """
    Scores an incoming transaction using the hybrid ML pipeline and historical database context.
    Persists the scored transaction and automatically generates alerts for high-risk actions.
    """
    txn_dict = payload.model_dump()

    # Synchronize field aliases between Indian schema and legacy schema
    amt = txn_dict.get("amount_inr")
    if amt is None:
        amt = txn_dict.get("amount") or 0.0
    txn_dict["amount"] = amt
    txn_dict["amount_inr"] = amt

    sender = txn_dict.get("sender_id") or txn_dict.get("customer_id") or txn_dict.get("card_id")
    if sender:
        txn_dict.setdefault("sender_id", sender)
        txn_dict.setdefault("customer_id", sender)
        txn_dict.setdefault("card_id", sender)

    bene = txn_dict.get("beneficiary_id") or txn_dict.get("merchant_id")
    if bene:
        txn_dict.setdefault("beneficiary_id", bene)
        txn_dict.setdefault("merchant_id", bene)

    # Ensure transaction ID exists and is unique
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txn_id = txn_dict.get("transaction_id")
    if not txn_id:
        txn_id = f"TXN_LIVE_{int(time.time() * 1000)}"
        txn_dict["transaction_id"] = txn_id
    else:
        # Check if ID already exists to prevent duplicate key error
        existing = db.query(TransactionORM.id).filter(TransactionORM.transaction_id == txn_id).first()
        if existing:
            txn_id = f"{txn_id}_{int(time.time() * 1000) % 10000}"
            txn_dict["transaction_id"] = txn_id

    if not txn_dict.get("timestamp"):
        txn_dict["timestamp"] = now_str

    # Score with historical context from DB (leakage-safe)
    res = predict_single_transaction(txn_dict, db=db)

    decision = res["decision"]
    risk_score = res["risk_score"]
    risk_cat = res.get("risk_category", "LOW_RISK")
    reasons = res.get("reasons", [])

    status_str = "Approved"
    if decision == "Block":
        status_str = "Declined"
    elif decision == "Manual Review":
        status_str = "Under Review"

    # Persist to transactions table
    db_txn = TransactionORM(
        transaction_id=txn_id,
        timestamp=txn_dict["timestamp"],
        amount_inr=amt,
        channel=txn_dict.get("channel") or "UPI_P2P",
        transaction_type=txn_dict.get("transaction_type") or "P2P_TRANSFER",
        sender_id=txn_dict.get("sender_id"),
        beneficiary_id=txn_dict.get("beneficiary_id"),
        sender_vpa=txn_dict.get("sender_vpa"),
        beneficiary_vpa=txn_dict.get("beneficiary_vpa"),
        merchant_id=txn_dict.get("merchant_id"),
        merchant_category=txn_dict.get("merchant_category") or "p2p_transfer",
        device_id=txn_dict.get("device_id"),
        is_new_device=txn_dict.get("is_new_device", 0),
        sim_change_flag=txn_dict.get("sim_change_flag", 0),
        ip_location_state=txn_dict.get("ip_location_state"),
        transaction_status="SUCCESS",
        # Legacy fields
        card_id=txn_dict.get("card_id"),
        customer_id=txn_dict.get("customer_id"),
        amount=amt,
        currency=txn_dict.get("currency") or "INR",
        country=txn_dict.get("country") or "IN",
        billing_country=txn_dict.get("billing_country") or "IN",
        ip_address=txn_dict.get("ip_address"),
        bin_range=txn_dict.get("bin_range"),
        segment=txn_dict.get("segment") or "UPI P2P",
        is_fraud=1 if decision == "Block" else 0,
        risk_score=risk_score,
        decision=decision,
        risk_category=risk_cat,
        reasons=json.dumps(reasons),
        status=status_str,
        model_version=res.get("model_version", "v1.0.0-xgb-iso-hybrid"),
        scored_at=now_str,
        source="api",
    )
    db.add(db_txn)

    # Automatically generate alerts for non-Allow transactions
    if decision in ["Block", "Manual Review"]:
        alert_code = f"ALT-{int(time.time() * 1000) % 1000000:06d}"
        
        # New fraud alert
        fraud_alert = FraudAlertORM(
            alert_id=f"FA-{alert_code}",
            transaction_id=txn_id,
            risk_score=risk_score,
            risk_category=risk_cat,
            reasons=json.dumps(reasons),
            review_status="OPEN",
            model_version=res.get("model_version", "v1.0.0-xgb-iso-hybrid"),
        )
        db.add(fraud_alert)

        # Legacy alert for frontend compatibility
        top_reason = reasons[0] if reasons else "High risk payment flagged"
        legacy_alert = AlertORM(
            alert_code=alert_code,
            title=f"{top_reason} on {txn_id}",
            segment=txn_dict.get("segment") or txn_dict.get("channel") or "UPI Payments",
            time_ago="Just now",
            status="Investigating" if decision == "Block" else "Monitoring",
            assignee="Risk Engine",
        )
        db.add(legacy_alert)

    db.commit()

    return res
