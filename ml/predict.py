"""
VaultGuard - Small Transaction Fraud Detection System
ml/predict.py

Prediction module for scoring incoming transactions and returning risk scores,
decisions (Allow, Manual Review, Block), and top 3 human-readable risk reasons.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Optional
import joblib
import numpy as np
import pandas as pd
import shap

from ml.features import extract_single_txn_features, FEATURE_COLUMNS

# Global model cache
_MODELS_CACHE = {}


def load_models():
    """Loads saved models from ml/saved_models/ directory."""
    if _MODELS_CACHE:
        return _MODELS_CACHE

    models_dir = Path(__file__).resolve().parent / "saved_models"

    xgb_path = models_dir / "xgboost_model.joblib"
    iso_path = models_dir / "isolation_forest.joblib"
    explainer_path = models_dir / "shap_explainer.joblib"
    feature_names_path = models_dir / "feature_names.joblib"

    if not xgb_path.exists() or not iso_path.exists():
        raise FileNotFoundError(
            f"Saved models not found in {models_dir}. Please run ml/train.py first."
        )

    _MODELS_CACHE["xgb_model"] = joblib.load(xgb_path)
    _MODELS_CACHE["iso_model"] = joblib.load(iso_path)
    _MODELS_CACHE["explainer"] = joblib.load(explainer_path)
    _MODELS_CACHE["feature_names"] = joblib.load(feature_names_path)

    return _MODELS_CACHE


def normalize_iso_score(scores):
    """Normalizes Isolation Forest score to 0-1 scale."""
    inv_scores = -scores
    min_val, max_val = -0.3, 0.3  # Estimated domain boundaries
    norm_scores = (inv_scores - min_val) / (max_val - min_val + 1e-5)
    return float(np.clip(norm_scores, 0.0, 1.0)[0])


def get_decision(risk_score: float) -> str:
    """Maps risk score (0-100) to business decisions: Allow, Manual Review, or Block."""
    if risk_score <= 40.0:
        return "Allow"
    elif risk_score <= 70.0:
        return "Manual Review"
    else:
        return "Block"


# Feature name to human readable reason mapping
REASON_LABELS = {
    "txn_count_1min": "Unusual velocity (high 1-min frequency)",
    "txn_count_10min": "Unusual velocity (rapid 10-min bursts)",
    "txn_count_1hour": "High transaction count in last hour",
    "device_count_24h": "New device surge on customer account",
    "geo_mismatch": "Geo mismatch (billing vs transaction country)",
    "high_risk_bin": "High-risk BIN range detected",
    "merchant_spike_ratio": "Merchant volume anomaly detected",
    "is_just_below_threshold": "Structuring indicator (amount just below limit)",
    "is_small_amount": "Card testing pattern (rapid micro-charge)",
    "amount_z_score": "Unusual amount deviation for card profile",
    "is_night": "Off-hours / late night transaction activity",
    "time_since_last_txn": "Extremely rapid succession since previous txn",
    "merchant_category_crypto_exchange": "High-risk merchant category (Crypto)",
}


def derive_reasons(
    feature_row: pd.Series, shap_values: np.ndarray, feature_names: List[str]
) -> List[str]:
    """
    Derives top 3 human-readable fraud risk reasons using SHAP feature contributions and domain rules.
    """
    reasons = []

    # 1. SHAP top contribution features
    # Sort features by positive SHAP contribution (increasing fraud probability)
    shap_impacts = list(zip(feature_names, shap_values, feature_row.values))
    shap_impacts.sort(key=lambda x: x[1], reverse=True)

    for name, shap_val, feat_val in shap_impacts:
        if len(reasons) >= 3:
            break

        if shap_val > 0.01:  # Positive contribution to fraud score
            if name in REASON_LABELS and REASON_LABELS[name] not in reasons:
                reasons.append(REASON_LABELS[name])

    # 2. Rule-based fallbacks if SHAP yields fewer than 3 reasons
    rule_checks = [
        (feature_row.get("geo_mismatch", 0) == 1, REASON_LABELS["geo_mismatch"]),
        (
            feature_row.get("high_risk_bin", 0) == 1,
            REASON_LABELS["high_risk_bin"],
        ),
        (
            feature_row.get("txn_count_10min", 0) >= 5,
            REASON_LABELS["txn_count_10min"],
        ),
        (
            feature_row.get("device_count_24h", 0) >= 3,
            REASON_LABELS["device_count_24h"],
        ),
        (
            feature_row.get("is_just_below_threshold", 0) == 1,
            REASON_LABELS["is_just_below_threshold"],
        ),
        (
            feature_row.get("merchant_spike_ratio", 0) > 3.0,
            REASON_LABELS["merchant_spike_ratio"],
        ),
        (
            feature_row.get("is_small_amount", 0) == 1
            and feature_row.get("txn_count_1min", 0) >= 3,
            REASON_LABELS["is_small_amount"],
        ),
        (
            feature_row.get("is_night", 0) == 1,
            REASON_LABELS["is_night"],
        ),
    ]

    for condition, label in rule_checks:
        if len(reasons) >= 3:
            break
        if condition and label not in reasons:
            reasons.append(label)

    # Fallback generic reasons if standard signals are low
    default_reasons = [
        "Normal baseline transaction parameters",
        "Verified device signature",
        "Standard transaction velocity",
    ]

    while len(reasons) < 3:
        for default in default_reasons:
            if default not in reasons:
                reasons.append(default)
            if len(reasons) >= 3:
                break

    return reasons[:3]


def score_transaction(
    txn: Dict, history_df: Optional[pd.DataFrame] = None
) -> Dict:
    """
    Evaluates a single transaction dictionary and returns risk_score, decision, and top 3 reasons.

    Args:
        txn: Dictionary of transaction attributes
        history_df: Optional historical DataFrame for velocity & historical z-scores context

    Returns:
        Dict: {
            "risk_score": float,
            "decision": str ("Allow" | "Manual Review" | "Block"),
            "reasons": List[str],
            "xgb_probability": float,
            "anomaly_score": float
        }
    """
    models = load_models()
    xgb_model = models["xgb_model"]
    iso_model = models["iso_model"]
    explainer = models["explainer"]
    feature_names = models["feature_names"]

    # Extract features
    features_df = extract_single_txn_features(txn, history_df)
    X_single = features_df[feature_names]

    # Predict probabilities & anomaly scores
    xgb_prob = float(xgb_model.predict_proba(X_single)[0, 1])
    iso_raw = float(iso_model.decision_function(X_single)[0])
    iso_score = normalize_iso_score(np.array([iso_raw]))

    # Calculate combined 0-100 risk score
    combined = (0.75 * xgb_prob) + (0.25 * iso_score)
    risk_score = round(float(np.clip(combined * 100.0, 0.0, 100.0)), 1)
    decision = get_decision(risk_score)

    # Compute SHAP values for local explainability
    shap_vals = explainer.shap_values(X_single)[0]
    reasons = derive_reasons(X_single.iloc[0], shap_vals, feature_names)

    return {
        "transaction_id": txn.get("transaction_id", "TXN_LIVE"),
        "risk_score": risk_score,
        "decision": decision,
        "reasons": reasons,
        "xgb_probability": round(xgb_prob, 4),
        "anomaly_score": round(iso_score, 4),
    }


if __name__ == "__main__":
    print("=" * 60)
    print(" VaultGuard - Single Transaction Real-Time Scoring Demo ")
    print("=" * 60)

    # Test sample: High-risk card testing transaction
    sample_txn = {
        "transaction_id": "TXN_TEST_DEMO_001",
        "timestamp": "2026-09-23 19:30:00",
        "card_id": "CARD_TEST_999",
        "customer_id": "CUST_TEST_999",
        "merchant_id": "MERCH_SPIKE_99",
        "merchant_category": "digital_goods",
        "amount": 2.50,
        "currency": "USD",
        "country": "US",
        "billing_country": "RU",  # Geo mismatch
        "device_id": "DEV_NEW_999",
        "ip_address": "185.220.101.5",
        "is_new_device": 1,
        "bin_range": "499999",  # High risk BIN
        "channel": "web",
        "segment": "AS Cards",
    }

    print("\nSample Transaction Payload:")
    for k, v in sample_txn.items():
        print(f"  {k:<20}: {v}")

    result = score_transaction(sample_txn)

    print("\n" + "-" * 60)
    print(" PREDICTION RESULT")
    print("-" * 60)
    print(f"Transaction ID : {result['transaction_id']}")
    print(f"Risk Score     : {result['risk_score']} / 100")
    print(f"Decision       : {result['decision']}")
    print(f"XGB Probability: {result['xgb_probability']}")
    print(f"Anomaly Score  : {result['anomaly_score']}")
    print("\nTop 3 Risk Reasons:")
    for i, reason in enumerate(result["reasons"], 1):
        print(f"  {i}. {reason}")
    print("=" * 60)
