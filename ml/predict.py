"""
VaultGuard - Indian Digital Payment Fraud Detection System
ml/predict.py

Inference module for scoring incoming transactions and returning risk scores,
decisions (Allow, Manual Review, Block), risk assistance categories, and top 3
evidence-based risk signals explained via SHAP feature attributions.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
import shap

from ml.features import FEATURE_COLUMNS, extract_single_txn_features

# Global model cache for low-latency scoring
_MODELS_CACHE = {}


def load_models() -> Dict:
    """Loads serialized models, explainer, and metrics from ml/saved_models/."""
    if _MODELS_CACHE:
        return _MODELS_CACHE

    models_dir = Path(__file__).resolve().parent / "saved_models"

    xgb_path = models_dir / "xgboost_model.joblib"
    iso_path = models_dir / "isolation_forest.joblib"
    explainer_path = models_dir / "shap_explainer.joblib"
    feature_names_path = models_dir / "feature_names.joblib"
    metrics_path = models_dir / "metrics.json"

    required_paths = [xgb_path, iso_path, explainer_path, feature_names_path]
    missing = [path.name for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Required model artifacts are missing: " + ", ".join(missing) + ". "
            "Run ml/train.py before starting scoring."
        )

    _MODELS_CACHE["xgb_model"] = joblib.load(xgb_path)
    _MODELS_CACHE["iso_model"] = joblib.load(iso_path)
    _MODELS_CACHE["explainer"] = joblib.load(explainer_path)
    _MODELS_CACHE["feature_names"] = joblib.load(feature_names_path)

    rf_path = models_dir / "random_forest.joblib"
    lr_path = models_dir / "logistic_regression.joblib"
    scaler_path = models_dir / "scaler.joblib"

    if rf_path.exists():
        _MODELS_CACHE["rf_model"] = joblib.load(rf_path)
    if lr_path.exists():
        _MODELS_CACHE["lr_model"] = joblib.load(lr_path)
    if scaler_path.exists():
        _MODELS_CACHE["scaler"] = joblib.load(scaler_path)

    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            _MODELS_CACHE["metrics"] = json.load(f)
    else:
        _MODELS_CACHE["metrics"] = {}

    return _MODELS_CACHE


def normalize_iso_score(raw_score: float, metrics: Dict) -> float:
    """Normalizes Isolation Forest score to a 0.0 - 1.0 anomaly scale."""
    bounds = metrics.get("iso_normalization_bounds", {})
    min_val = bounds.get("min_val", -0.3)
    max_val = bounds.get("max_val", 0.3)

    inv_score = -raw_score
    diff = max_val - min_val
    if diff <= 1e-7:
        return 0.0
    norm_score = (inv_score - min_val) / diff
    return float(np.clip(norm_score, 0.0, 1.0))


def get_decision(risk_score: float) -> str:
    """Maps risk score (0-100) to business assistance categories: Allow, Manual Review, or Block."""
    if risk_score <= 40.0:
        return "Allow"
    elif risk_score <= 70.0:
        return "Manual Review"
    else:
        return "Block"


def get_risk_category(risk_score: float) -> str:
    """Returns the standardized decision-support risk category."""
    if risk_score <= 40.0:
        return "LOW_RISK"
    elif risk_score <= 70.0:
        return "REVIEW"
    else:
        return "HIGH_RISK"


# Human-readable evidence labels for strongest risk signals
REASON_LABELS = {
    "high_risk_device_action": "High-risk device takeover: simultaneous new device & recent SIM swap",
    "sim_change_flag": "Recent SIM card change detected on account",
    "is_new_device": "Transaction originating from unverified new device",
    "is_new_beneficiary": "First-time transfer to unfamiliar beneficiary VPA",
    "merchant_spike_ratio": "Mule QR / merchant terminal abnormal volume spike",
    "is_just_below_threshold": "Structuring pattern: amount just below regulatory limit",
    "is_small_amount": "UPI micro-testing pattern (rapid low-value probe)",
    "amount_to_avg_ratio": "Abnormal amount surge relative to customer past average",
    "txn_count_1min": "Unusual micro-velocity (rapid 1-minute transaction frequency)",
    "txn_count_10min": "Unusual velocity burst in 10-minute window",
    "txn_count_1hour": "High transaction count in last hour",
    "txn_type_COLLECT_REQUEST": "Potential phishing collect-request approval",
    "is_night": "Off-hours / unusual late-night transaction activity",
    "time_since_last_txn": "Extremely rapid succession since previous transaction",
    "geo_mismatch": "Geographic mismatch detected",
    "high_risk_bin": "High-risk BIN / routing range detected",
}


def derive_reasons(
    feature_row: pd.Series, shap_values: np.ndarray, feature_names: List[str]
) -> List[str]:
    """
    Derives the top 3 human-readable fraud risk reasons using SHAP feature contributions
    and domain rule verifications.
    """
    reasons = []

    # 1. SHAP top contribution features (positive contribution pushing toward fraud)
    shap_impacts = list(zip(feature_names, shap_values, feature_row.values))
    shap_impacts.sort(key=lambda x: x[1], reverse=True)

    for name, shap_val, feat_val in shap_impacts:
        if len(reasons) >= 3:
            break
        if shap_val > 0.01:
            if name in REASON_LABELS and REASON_LABELS[name] not in reasons:
                reasons.append(REASON_LABELS[name])

    # 2. Domain rule checks if SHAP yields fewer than 3 reasons
    rule_checks = [
        (
            feature_row.get("high_risk_device_action", 0) == 1,
            REASON_LABELS["high_risk_device_action"],
        ),
        (
            feature_row.get("sim_change_flag", 0) == 1,
            REASON_LABELS["sim_change_flag"],
        ),
        (
            feature_row.get("txn_count_1min", 0) >= 3,
            REASON_LABELS["txn_count_1min"],
        ),
        (
            feature_row.get("txn_count_10min", 0) >= 4,
            REASON_LABELS["txn_count_10min"],
        ),
        (
            feature_row.get("merchant_spike_ratio", 0) >= 3.0,
            REASON_LABELS["merchant_spike_ratio"],
        ),
        (
            feature_row.get("is_just_below_threshold", 0) == 1,
            REASON_LABELS["is_just_below_threshold"],
        ),
        (
            feature_row.get("is_new_device", 0) == 1
            and feature_row.get("is_new_beneficiary", 0) == 1,
            REASON_LABELS["is_new_beneficiary"],
        ),
        (
            feature_row.get("is_night", 0) == 1,
            REASON_LABELS["is_night"],
        ),
        (
            feature_row.get("geo_mismatch", 0) == 1,
            REASON_LABELS["geo_mismatch"],
        ),
        (
            feature_row.get("high_risk_bin", 0) == 1,
            REASON_LABELS["high_risk_bin"],
        ),
    ]

    for condition, label in rule_checks:
        if len(reasons) >= 3:
            break
        if condition and label not in reasons:
            reasons.append(label)

    # Fallback reasons for legitimate / low-risk transactions
    default_reasons = [
        "Verified customer baseline parameters",
        "Established beneficiary history",
        "Standard digital transaction velocity",
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
    Evaluates a single transaction dictionary and returns risk score, decision,
    assistance category, and top 3 evidence-based risk reasons.

    Args:
        txn: Dictionary of transaction attributes
        history_df: Optional historical DataFrame for velocity & historical context

    Returns:
        Dict: {
            "transaction_id": str,
            "risk_score": float (0-100),
            "decision": str ("Allow" | "Manual Review" | "Block"),
            "risk_category": str ("LOW_RISK" | "REVIEW" | "HIGH_RISK"),
            "reasons": List[str],
            "xgb_probability": float,
            "anomaly_score": float,
            "fraud_probability": float,
            "model_used": str
        }
    """
    models = load_models()
    xgb_model = models["xgb_model"]
    iso_model = models["iso_model"]
    explainer = models["explainer"]
    feature_names = models["feature_names"]
    metrics = models["metrics"]

    # Extract features matching trained schema
    features_df = extract_single_txn_features(txn, history_df)
    X_single = features_df[feature_names]

    # Predict supervised fraud probability & unsupervised anomaly score
    xgb_prob = float(xgb_model.predict_proba(X_single)[0, 1])
    iso_raw = float(iso_model.decision_function(X_single)[0])
    iso_norm = normalize_iso_score(iso_raw, metrics)

    # Compute hybrid risk score (0 to 100)
    combined = (0.75 * xgb_prob) + (0.25 * iso_norm)
    risk_score = round(float(np.clip(combined * 100.0, 0.0, 100.0)), 1)
    decision = get_decision(risk_score)
    risk_category = get_risk_category(risk_score)

    # Compute SHAP values for local explainability
    shap_vals = explainer.shap_values(X_single)[0]
    reasons = derive_reasons(X_single.iloc[0], shap_vals, feature_names)

    return {
        "transaction_id": txn.get("transaction_id", "TXN_LIVE"),
        "risk_score": risk_score,
        "decision": decision,
        "risk_category": risk_category,
        "reasons": reasons,
        "xgb_probability": round(xgb_prob, 4),
        "anomaly_score": round(iso_norm, 4),
        "fraud_probability": round(xgb_prob, 4),
        "model_used": "XGBoost + Isolation Forest Hybrid",
    }


if __name__ == "__main__":
    print("=" * 60)
    print(" VaultGuard - Real-Time Indian Payment Scoring Demo ")
    print("=" * 60)

    # Sample test transaction: High-risk SIM swap + new device takeover
    sample_txn = {
        "transaction_id": "TXN_TEST_DEMO_UPI_01",
        "timestamp": "2026-10-12 18:30:00",
        "amount_inr": 8500.00,
        "channel": "UPI_P2P",
        "transaction_type": "P2P_TRANSFER",
        "sender_id": "CUST_IND_9999",
        "beneficiary_id": "MULE_DRAIN_101",
        "sender_vpa": "victim.user@okhdfcbank",
        "beneficiary_vpa": "mule.account@paytm",
        "device_id": "DEV_NEW_999",
        "is_new_device": 1,
        "sim_change_flag": 1,  # Critical account takeover indicator
        "ip_location_state": "Maharashtra",
        "is_fraud": 0,
    }

    print("\nSample Transaction Payload:")
    for k, v in sample_txn.items():
        print(f"  {k:<22}: {v}")

    result = score_transaction(sample_txn)

    print("\n" + "-" * 60)
    print(" PREDICTION RESULT")
    print("-" * 60)
    print(f"Transaction ID   : {result['transaction_id']}")
    print(f"Risk Score       : {result['risk_score']} / 100")
    print(f"Decision         : {result['decision']}")
    print(f"Risk Category    : {result['risk_category']}")
    print(f"Fraud Probability: {result['xgb_probability'] * 100:.1f}%")
    print(f"Anomaly Score    : {result['anomaly_score'] * 100:.1f}%")
    print("\nTop Evidence Signals:")
    for i, reason in enumerate(result["reasons"], 1):
        print(f"  {i}. {reason}")
    print("=" * 60)
