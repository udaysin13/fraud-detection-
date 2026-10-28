"""
VaultGuard - Analytics & Dashboard Endpoints

Provides:
- High-level overview metrics & fraud rates
- Summary risk metrics and top risk contributor calculations
- Time-series trend aggregation (24h, 7d, 30d)
- CSV transaction export
"""

from collections import Counter
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
from backend.app.schemas.pydantic_schemas import (
    RiskScoreSummary,
    TrendPoint,
    TopContributor,
    AnalyticsOverview,
)

router = APIRouter(prefix="/api", tags=["Analytics"])


@router.get("/analytics/overview", response_model=AnalyticsOverview)
def get_analytics_overview(db: Session = Depends(get_db)):
    """
    Returns high-level statistics across all transactions in the database.
    """
    total = db.query(TransactionORM).count()
    if total == 0:
        return AnalyticsOverview(
            total_transactions=0,
            dataset_fraud_labels=0,
            total_fraud_flagged=0,
            total_blocked=0,
            total_review=0,
            total_allowed=0,
            fraud_rate_pct=0.0,
            avg_risk_score=0.0,
        )

    blocked = db.query(TransactionORM).filter(TransactionORM.decision == "Block").count()
    review = db.query(TransactionORM).filter(TransactionORM.decision == "Manual Review").count()
    allowed = db.query(TransactionORM).filter(TransactionORM.decision == "Allow").count()
    dataset_fraud_labels = db.query(TransactionORM).filter(TransactionORM.is_fraud == 1).count()
    flagged = db.query(TransactionORM).filter(TransactionORM.risk_score > 40.0).count()

    avg_score = db.query(func.avg(TransactionORM.risk_score)).scalar() or 0.0

    return AnalyticsOverview(
        total_transactions=total,
        dataset_fraud_labels=dataset_fraud_labels,
        total_fraud_flagged=flagged,
        total_blocked=blocked,
        total_review=review,
        total_allowed=allowed,
        fraud_rate_pct=round((flagged / total) * 100.0, 2),
        avg_risk_score=round(float(avg_score), 2),
    )


@router.get("/risk-score", response_model=RiskScoreSummary)
def get_risk_score_summary(db: Session = Depends(get_db)):
    """
    Returns summary analytics: total flagged transaction count (risk_score > 40),
    percentage change, and top risk contributors computed from recent flagged transactions.
    """
    total_txns = db.query(TransactionORM).count()
    flagged_count = (
        db.query(TransactionORM)
        .filter(TransactionORM.risk_score > 40.0)
        .count()
    )

    # Compute top contributors dynamically from recent flagged transactions' reasons
    recent_flagged = (
        db.query(TransactionORM.reasons)
        .filter(TransactionORM.risk_score > 40.0)
        .order_by(TransactionORM.id.desc())
        .limit(1000)
        .all()
    )

    reason_counter = Counter()
    for (r_json,) in recent_flagged:
        if r_json:
            try:
                r_list = json.loads(r_json)
                if isinstance(r_list, list):
                    for reason in r_list:
                        # Exclude standard baseline reasons
                        if not any(w in reason.lower() for w in ["standard", "verified", "baseline"]):
                            reason_counter[reason] += 1
            except Exception:
                pass

    total_reasons = sum(reason_counter.values())
    top_contributors = []
    if total_reasons > 0:
        for name, count in reason_counter.most_common(5):
            pct = round((count / total_reasons) * 100.0, 1)
            top_contributors.append({"name": name, "percentage": pct})

    pct_change = round((flagged_count / max(total_txns, 1)) * 100.0, 1)

    return {
        "flagged_count": flagged_count,
        "pct_change": min(pct_change, 99.9),
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
    txns = (
        db.query(
            TransactionORM.timestamp,
            TransactionORM.risk_score,
            TransactionORM.decision,
        )
        .order_by(TransactionORM.timestamp.desc())
        .limit(3000)
        .all()
    )

    if not txns:
        return []

    df = pd.DataFrame(txns, columns=["timestamp", "risk_score", "decision"])
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp_dt"])

    range_window = {
        "24h": pd.Timedelta(hours=24),
        "7d": pd.Timedelta(days=7),
        "30d": pd.Timedelta(days=30),
    }[range]
    window_start = pd.Timestamp.now(tz="UTC") - range_window
    df = df[df["timestamp_dt"].notna()]
    df = df[df["timestamp_dt"] >= window_start]
    used_historical_fallback = False
    if df.empty:
        # Seed/demo datasets often contain historical timestamps. Show the latest
        # available persisted records instead of returning an empty dashboard chart.
        df = pd.DataFrame(txns, columns=["timestamp", "risk_score", "decision"])
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df = df.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt").tail(3000)
        used_historical_fallback = not df.empty
    if df.empty:
        return []

    decisions = df["decision"].fillna("").astype(str).str.strip().str.lower()
    df["is_blocked"] = decisions.isin(["block", "blocked"])
    df["is_manual_review"] = decisions.isin(["manual review", "manual_review", "review"])

    # If using historical fallback, bucket by actual stored dates so users can see
    # where the available records came from; never fabricate transaction counts.
    if range == "24h" and not used_historical_fallback:
        df["time_group"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:00")
    elif range == "24h":
        df["time_group"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:00")
    else:
        df["time_group"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d")

    grouped = (
        df.groupby("time_group")
        .agg(
            suspicious=("risk_score", lambda s: (pd.to_numeric(s, errors="coerce").fillna(0) > 40.0).sum()),
            blocked=("is_blocked", "sum"),
            manual_review=("is_manual_review", "sum"),
        )
        .reset_index()
        .sort_values("time_group")
        .tail({"24h": 24, "7d": 7, "30d": 30}[range])
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


def sanitize_csv_cell(val):
    """
    Sanitizes values to prevent CSV / Spreadsheet formula injection (CWE-1236).
    Prepends a single quote if the string begins with =, +, -, @, \\t, or \\r.
    """
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


@router.get("/export")
def export_transactions_csv(
    type: str = Query("csv", pattern="^(csv)$"),
    db: Session = Depends(get_db),
):
    """
    Exports scored transactions to CSV file stream.
    Includes both Indian and legacy fields with cell sanitization against formula injection.
    """
    txns = db.query(TransactionORM).order_by(TransactionORM.id.desc()).limit(10000).all()

    data = []
    for t in txns:
        data.append(
            {
                "transaction_id": sanitize_csv_cell(t.transaction_id),
                "timestamp": sanitize_csv_cell(t.timestamp),
                "channel": sanitize_csv_cell(t.channel),
                "sender_id": sanitize_csv_cell(t.sender_id),
                "beneficiary_id": sanitize_csv_cell(t.beneficiary_id),
                "amount_inr": t.amount_inr,
                "amount": t.amount,
                "currency": sanitize_csv_cell(t.currency),
                "risk_score": t.risk_score,
                "decision": sanitize_csv_cell(t.decision),
                "risk_category": sanitize_csv_cell(t.risk_category),
                "reasons": sanitize_csv_cell(t.reasons),
                "status": sanitize_csv_cell(t.status),
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
