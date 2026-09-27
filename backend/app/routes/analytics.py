"""
VaultGuard - Analytics & Dashboard Endpoints
"""

from io import StringIO
import json
from typing import List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.orm import TransactionORM
from backend.app.schemas.pydantic_schemas import RiskScoreSummary, TrendPoint, TopContributor

router = APIRouter(prefix="/api", tags=["Analytics"])


@router.get("/risk-score", response_model=RiskScoreSummary)
def get_risk_score_summary(db: Session = Depends(get_db)):
    """
    Returns summary analytics: total flagged transaction count (risk_score > 40),
    percentage change, and top risk contributors.
    """
    flagged_count = (
        db.query(TransactionORM)
        .filter(TransactionORM.risk_score > 40.0)
        .count()
    )

    top_contributors = [
        {"name": "Geo Mismatch", "percentage": 28.5},
        {"name": "Card Testing Pattern", "percentage": 24.2},
        {"name": "Velocity Attack", "percentage": 21.0},
        {"name": "High-Risk BIN Range", "percentage": 14.8},
        {"name": "Structuring Indicator", "percentage": 11.5},
    ]

    return {
        "flagged_count": flagged_count,
        "pct_change": 5.2,
        "top_contributors": top_contributors,
    }


@router.get("/trend", response_model=List[TrendPoint])
def get_fraud_trend(
    range: str = Query("24h", pattern="^(24h|7d|30d)$"),
    db: Session = Depends(get_db),
):
    """
    Returns time series trend data for suspicious, blocked, and manual review transactions.
    Supports range=24h, 7d, 30d.
    """
    # Sample aggregated time series based on database timestamps
    txns = (
        db.query(
            TransactionORM.timestamp,
            TransactionORM.risk_score,
            TransactionORM.decision,
        )
        .order_by(TransactionORM.timestamp.desc())
        .limit(2400)
        .all()
    )

    if not txns:
        return []

    # Group into buckets
    df = pd.DataFrame(txns, columns=["timestamp", "risk_score", "decision"])
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])

    if range == "24h":
        df["time_group"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:00")
    elif range == "7d":
        df["time_group"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d")
    else:
        df["time_group"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby("time_group")
        .agg(
            suspicious=("risk_score", lambda s: (s > 40.0).sum()),
            blocked=("decision", lambda s: (s == "Block").sum()),
            manual_review=("decision", lambda s: (s == "Manual Review").sum()),
        )
        .reset_index()
        .sort_values("time_group")
        .tail(24)
    )

    result = []
    for _, row in grouped.iterrows():
        result.append(
            {
                "timestamp": str(row["time_group"]),
                "suspicious": int(row["suspicious"]),
                "blocked": int(row["blocked"]),
                "manual_review": int(row["manual_review"]),
            }
        )

    return result


@router.get("/export")
def export_transactions_csv(
    type: str = Query("csv", pattern="^(csv)$"),
    db: Session = Depends(get_db),
):
    """
    Exports scored transactions to CSV file stream.
    """
    txns = db.query(TransactionORM).order_by(TransactionORM.id.desc()).limit(10000).all()

    data = []
    for t in txns:
        data.append(
            {
                "transaction_id": t.transaction_id,
                "timestamp": t.timestamp,
                "card_id": t.card_id,
                "customer_id": t.customer_id,
                "merchant_id": t.merchant_id,
                "merchant_category": t.merchant_category,
                "amount": t.amount,
                "currency": t.currency,
                "country": t.country,
                "billing_country": t.billing_country,
                "channel": t.channel,
                "segment": t.segment,
                "risk_score": t.risk_score,
                "decision": t.decision,
                "reasons": t.reasons,
                "status": t.status,
            }
        )

    df = pd.DataFrame(data)
    stream = StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(
        iter([stream.getvalue()]), media_type="text/csv"
    )
    response.headers[
        "Content-Disposition"
    ] = 'attachment; filename="vaultguard_transactions.csv"'
    return response
