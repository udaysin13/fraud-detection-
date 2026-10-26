"""
VaultGuard - Production ML Service Integration

Provides:
1. Singleton model loading and health monitoring.
2. Bounded, leakage-safe historical feature retrieval from SQLite / SQLAlchemy.
3. Hybrid real-time transaction scoring (XGBoost + Isolation Forest + SHAP).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.orm import TransactionORM
from ml.predict import load_models, score_transaction
from ml.train import train_models
from backend.app.services.risk_rules import evaluate_transaction_rules, recommended_action

_MODEL_CACHE: Optional[Dict] = None


def get_cached_models() -> Dict:
    """Retrieves or loads the ML model artifacts once into memory."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        _MODEL_CACHE = load_models()
    return _MODEL_CACHE


def get_model_health() -> Dict:
    """Checks model artifacts readiness and metadata."""
    models_dir = PROJECT_ROOT / "ml" / "saved_models"
    xgb_path = models_dir / "xgboost_model.joblib"
    iso_path = models_dir / "isolation_forest.joblib"
    metrics_path = models_dir / "metrics.json"

    is_ready = xgb_path.exists() and iso_path.exists()
    metrics = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, "r") as f:
                metrics = json.load(f)
        except Exception:
            metrics = {}

    return {
        "status": "ready" if is_ready else "not_found",
        "artifacts_exist": is_ready,
        "models_directory": str(models_dir),
        "selected_model": metrics.get("selected_model", "XGBoost"),
        "metrics_summary": {
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1_score": metrics.get("f1_score"),
            "roc_auc": metrics.get("roc_auc"),
            "pr_auc": metrics.get("pr_auc"),
            "selected_threshold": metrics.get("selected_threshold"),
        },
    }


def fetch_historical_context(
    txn: Dict,
    db: Optional[Session] = None,
    max_lookback_txns: int = 50,
) -> Optional[pd.DataFrame]:
    """
    Retrieves prior transaction history for the sender/customer to calculate
    point-in-time velocity and historical baseline features without future leakage.

    Guarantees:
    1. Strictly filter `timestamp < current_txn_timestamp`.
    2. Scoped by sender_id (or customer_id / card_id fallback).
    3. Bounded to recent records (max 50) for ultra-low latency.
    """
    if db is None:
        return None

    sender = (
        txn.get("sender_id")
        or txn.get("customer_id")
        or txn.get("card_id")
    )
    if not sender:
        return None

    current_ts = txn.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Bounded, chronological query for prior transactions only
        query = (
            db.query(
                TransactionORM.transaction_id,
                TransactionORM.timestamp,
                TransactionORM.amount_inr,
                TransactionORM.amount,
                TransactionORM.channel,
                TransactionORM.transaction_type,
                TransactionORM.sender_id,
                TransactionORM.customer_id,
                TransactionORM.beneficiary_id,
                TransactionORM.merchant_id,
                TransactionORM.merchant_category,
                TransactionORM.device_id,
                TransactionORM.is_new_device,
                TransactionORM.sim_change_flag,
                TransactionORM.ip_location_state,
                TransactionORM.country,
                TransactionORM.billing_country,
                TransactionORM.bin_range,
            )
            .filter(
                and_(
                    (TransactionORM.sender_id == sender) | (TransactionORM.customer_id == sender) | (TransactionORM.card_id == sender),
                    TransactionORM.timestamp < current_ts,
                )
            )
            .order_by(TransactionORM.timestamp.desc())
            .limit(max_lookback_txns)
        )

        rows = query.all()
        if not rows:
            return None

        # Build DataFrame with chronological ordering (oldest to newest prior records)
        records = [
            {
                "transaction_id": r.transaction_id,
                "timestamp": r.timestamp,
                "amount": r.amount if r.amount is not None else (r.amount_inr or 0.0),
                "amount_inr": r.amount_inr if r.amount_inr is not None else (r.amount or 0.0),
                "channel": r.channel or "UPI_P2P",
                "transaction_type": r.transaction_type or "P2P_TRANSFER",
                "sender_id": r.sender_id or r.customer_id,
                "customer_id": r.customer_id or r.sender_id,
                "beneficiary_id": r.beneficiary_id or r.merchant_id,
                "merchant_id": r.merchant_id or r.beneficiary_id,
                "merchant_category": r.merchant_category or "p2p_transfer",
                "device_id": r.device_id,
                "is_new_device": r.is_new_device or 0,
                "sim_change_flag": r.sim_change_flag or 0,
                "ip_location_state": r.ip_location_state,
                "country": r.country or "IN",
                "billing_country": r.billing_country or "IN",
                "bin_range": r.bin_range or "",
            }
            for r in reversed(rows)
        ]

        return pd.DataFrame(records)
    except Exception as e:
        # Fall back gracefully to standalone extraction if DB query fails
        return None


def predict_single_transaction(
    txn: Dict, db: Optional[Session] = None
) -> Dict:
    """
    Scores an incoming transaction with historical context if available.
    Returns response compatible with both frontend legacy and Indian payment schemas.
    """
    # 1. Fetch prior history bounded to current entity
    history_df = fetch_historical_context(txn, db=db)

    # 2. Score via hybrid ML models
    scoring_result = score_transaction(txn, history_df=history_df)

    # Rules are transparent decision-support signals and do not modify ML outputs.
    rule_signals = evaluate_transaction_rules(txn, history_df=history_df, db=db)
    scoring_result["rule_signals"] = rule_signals
    scoring_result["recommended_action"] = recommended_action(
        scoring_result["risk_category"], rule_signals
    )

    # 3. Augment with metadata
    scoring_result["model_version"] = "v1.0.0-xgb-iso-hybrid"
    scoring_result["scoring_timestamp"] = datetime.now(timezone.utc).isoformat()

    return scoring_result


def trigger_retraining() -> Dict:
    """Triggers ML model pipeline training and reloads cache."""
    global _MODEL_CACHE
    train_models()
    _MODEL_CACHE = None  # Invalidate cache to force reload

    models_dir = PROJECT_ROOT / "ml" / "saved_models"
    metrics_path = models_dir / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            return json.load(f)
    return {"status": "retrained"}
