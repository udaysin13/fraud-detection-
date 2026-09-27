"""
VaultGuard - Transactions & Real-Time Prediction Router
"""

import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.database import get_db
from backend.app.models.orm import TransactionORM
from backend.app.schemas.pydantic_schemas import (
    TransactionResponse,
    TransactionPredictRequest,
    PredictionResponse,
)
from backend.app.services.ml_service import predict_single_transaction

router = APIRouter(prefix="/api", tags=["Transactions & Scoring"])


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    decision: Optional[str] = None,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated transactions with optional multi-attribute filtering.
    """
    query = db.query(TransactionORM)

    if decision:
        query = query.filter(TransactionORM.decision == decision)
    if segment:
        query = query.filter(TransactionORM.segment == segment)
    if min_amount is not None:
        query = query.filter(TransactionORM.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(TransactionORM.amount <= max_amount)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                TransactionORM.transaction_id.ilike(search_filter),
                TransactionORM.card_id.ilike(search_filter),
                TransactionORM.customer_id.ilike(search_filter),
                TransactionORM.merchant_id.ilike(search_filter),
            )
        )

    offset = (page - 1) * limit
    results = (
        query.order_by(TransactionORM.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Format JSON reasons string into Python list for response schema
    out = []
    for r in results:
        reasons_list = []
        if r.reasons:
            try:
                reasons_list = json.loads(r.reasons)
            except Exception:
                reasons_list = [r.reasons]

        item = TransactionResponse(
            id=r.id,
            transaction_id=r.transaction_id,
            timestamp=r.timestamp,
            card_id=r.card_id,
            customer_id=r.customer_id,
            merchant_id=r.merchant_id,
            merchant_category=r.merchant_category,
            amount=r.amount,
            currency=r.currency,
            country=r.country,
            billing_country=r.billing_country,
            device_id=r.device_id,
            ip_address=r.ip_address,
            is_new_device=r.is_new_device,
            bin_range=r.bin_range,
            channel=r.channel,
            segment=r.segment,
            is_fraud=r.is_fraud,
            risk_score=r.risk_score,
            decision=r.decision,
            reasons=reasons_list,
            status=r.status,
        )
        out.append(item)

    return out


@router.post("/predict", response_model=PredictionResponse)
def score_single_transaction_api(
    payload: TransactionPredictRequest, db: Session = Depends(get_db)
):
    """
    Scores an incoming real-time transaction and returns risk score, decision, and top 3 reasons.
    """
    txn_dict = payload.model_dump()
    res = predict_single_transaction(txn_dict)

    # Save incoming prediction to database
    db_txn = TransactionORM(
        transaction_id=res["transaction_id"],
        timestamp=payload.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        card_id=payload.card_id,
        customer_id=payload.customer_id,
        merchant_id=payload.merchant_id,
        merchant_category=payload.merchant_category,
        amount=payload.amount,
        currency=payload.currency,
        country=payload.country,
        billing_country=payload.billing_country,
        device_id=payload.device_id,
        ip_address=payload.ip_address,
        is_new_device=payload.is_new_device,
        bin_range=payload.bin_range,
        channel=payload.channel,
        segment=payload.segment,
        is_fraud=0,
        risk_score=res["risk_score"],
        decision=res["decision"],
        reasons=json.dumps(res["reasons"]),
        status="Declined" if res["decision"] == "Block" else ("Under Review" if res["decision"] == "Manual Review" else "Approved"),
    )
    db.add(db_txn)
    db.commit()

    return res
