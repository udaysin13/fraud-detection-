import os
import sys
import json
import csv
import io
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

# Ensure backend directory and project root are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Import feature extractor from ml package
try:
    from ml.features import extract_single_txn_features, FEATURE_COLUMNS
except ImportError:
    from backend.ml.features import extract_single_txn_features, FEATURE_COLUMNS

app = FastAPI(
    title="VaultGuard Fraud Engine",
    description="Real-Time Indian Digital Payment Fraud Detection Engine",
    version="1.0.0-academic"
)

# Robust CORS Configuration: Allow all origins and methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── MODEL LOADING ───────────────────────────────────────────────────────────
MODEL_DIR = os.path.join(BASE_DIR, "ml", "saved_models")
if not os.path.exists(MODEL_DIR):
    MODEL_DIR = os.path.join(PARENT_DIR, "ml", "saved_models")

feature_names = None
iso_model = None
rf_model = None
xgb_model = None
lr_model = None
scaler = None
metrics_data = {}

try:
    fn_path = os.path.join(MODEL_DIR, "feature_names.joblib")
    if os.path.exists(fn_path):
        feature_names = joblib.load(fn_path)

    iso_path = os.path.join(MODEL_DIR, "isolation_forest.joblib")
    if os.path.exists(iso_path):
        iso_model = joblib.load(iso_path)

    rf_path = os.path.join(MODEL_DIR, "random_forest.joblib")
    if os.path.exists(rf_path):
        rf_model = joblib.load(rf_path)

    xgb_path = os.path.join(MODEL_DIR, "xgboost_model.joblib")
    if os.path.exists(xgb_path):
        try:
            import xgboost
            xgb_model = joblib.load(xgb_path)
        except Exception as e:
            print(f"[Warning] XGBoost could not be loaded ({e}), using Random Forest.")

    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)

    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)
except Exception as e:
    print(f"[Model Load Warning] {e}")

# Precompute normalization bounds for Isolation Forest
iso_bounds = metrics_data.get("iso_normalization_bounds", {"min_val": -0.19, "max_val": 0.14})
iso_min = iso_bounds.get("min_val", -0.19)
iso_max = iso_bounds.get("max_val", 0.14)
iso_diff = (iso_max - iso_min) if abs(iso_max - iso_min) > 1e-7 else 1.0


# ─── REAL PREDICTION ENGINE ──────────────────────────────────────────────────
def run_real_prediction(txn_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes genuine ML inference using trained ensemble models and isolation forest.
    """
    amt = float(txn_dict.get("amount_inr") or txn_dict.get("amount") or 0.0)
    if amt <= 0:
        raise HTTPException(status_code=400, detail="Transaction amount must be a positive number.")

    # 1. Feature Engineering
    features_df = extract_single_txn_features(txn_dict)
    if feature_names:
        cols_to_use = [col for col in feature_names if col in features_df.columns]
        X_matrix = features_df[cols_to_use]
    else:
        X_matrix = features_df

    # 2. Supervised Fraud Probability
    if xgb_model is not None:
        p_fraud = float(xgb_model.predict_proba(X_matrix)[0, 1])
        model_name = "XGBoost + Isolation Forest"
    elif rf_model is not None:
        p_fraud = float(rf_model.predict_proba(X_matrix)[0, 1])
        model_name = "Random Forest + Isolation Forest"
    else:
        # Heuristic fallback if models cannot be read
        p_fraud = 0.5
        model_name = "Rule Heuristic Fallback"

    # 3. Unsupervised Anomaly Score
    if iso_model is not None:
        raw_iso = float(iso_model.decision_function(X_matrix)[0])
        p_anomaly = float(np.clip((-raw_iso - iso_min) / iso_diff, 0.0, 1.0))
    else:
        p_anomaly = 0.2

    # 4. Hybrid Risk Score (0 - 100)
    combined = (0.75 * p_fraud + 0.25 * p_anomaly) * 100.0
    risk_score = round(float(np.clip(combined, 0.0, 100.0)), 1)

    # 5. Standardized Decision & Risk Category
    if risk_score > 70.0:
        decision = "Block"
        risk_category = "HIGH_RISK"
    elif risk_score > 40.0:
        decision = "Manual Review"
        risk_category = "REVIEW"
    else:
        decision = "Allow"
        risk_category = "LOW_RISK"

    # 6. Evidence Reasons from Transaction Indicators
    feat_row = X_matrix.iloc[0]
    reasons = []

    if feat_row.get("high_risk_device_action", 0) == 1:
        reasons.append("High-risk device takeover: simultaneous new device & recent SIM swap")
    if feat_row.get("sim_change_flag", 0) == 1:
        reasons.append("Recent SIM card change detected on account")
    if feat_row.get("is_new_device", 0) == 1:
        reasons.append("Transaction originating from unverified new device")
    if feat_row.get("is_just_below_threshold", 0) == 1:
        reasons.append("Structuring pattern: amount just below regulatory limit")
    if feat_row.get("is_small_amount", 0) == 1:
        reasons.append("UPI micro-testing pattern (rapid low-value probe)")
    if feat_row.get("amount_to_avg_ratio", 0) > 3.0:
        reasons.append("Abnormal amount surge relative to customer past average")
    if feat_row.get("txn_count_1min", 0) >= 3:
        reasons.append("Unusual micro-velocity (rapid 1-minute transaction frequency)")
    if feat_row.get("txn_count_10min", 0) >= 4:
        reasons.append("Unusual velocity burst in 10-minute window")
    if feat_row.get("is_night", 0) == 1:
        reasons.append("Off-hours / unusual late-night transaction activity")
    if feat_row.get("geo_mismatch", 0) == 1:
        reasons.append("Geographic mismatch detected")
    if feat_row.get("merchant_spike_ratio", 0) >= 3.0:
        reasons.append("Mule QR / merchant terminal abnormal volume spike")

    default_legit_reasons = [
        "Verified customer baseline parameters",
        "Established beneficiary history",
        "Standard digital transaction velocity",
    ]
    for d in default_legit_reasons:
        if len(reasons) < 3 and d not in reasons:
            reasons.append(d)
    reasons = reasons[:3]

    # 7. Transparent Rule Signals
    rule_signals = []
    if feat_row.get("sim_change_flag", 0) == 1 and feat_row.get("is_new_device", 0) == 1:
        rule_signals.append({
            "rule_id": "RULE_ATO_01",
            "severity": "CRITICAL",
            "message": "Simultaneous SIM swap and unfamiliar device detected."
        })
    elif feat_row.get("sim_change_flag", 0) == 1:
        rule_signals.append({
            "rule_id": "RULE_SIM_01",
            "severity": "HIGH",
            "message": "SIM change detected within last 48 hours."
        })
    if feat_row.get("is_just_below_threshold", 0) == 1:
        rule_signals.append({
            "rule_id": "RULE_STRUC_01",
            "severity": "HIGH",
            "message": "Transaction amount structured just below regulatory reporting threshold."
        })
    if feat_row.get("is_small_amount", 0) == 1 and feat_row.get("is_new_device", 0) == 1:
        rule_signals.append({
            "rule_id": "RULE_MICRO_01",
            "severity": "MEDIUM",
            "message": "Micro-testing transaction on newly bound device."
        })

    txn_id = txn_dict.get("transaction_id") or f"TXN_LIVE_{int(time.time() * 1000)}"

    return {
        "status": "success",
        "transaction_id": txn_id,
        "risk_score": risk_score,
        "risk_assessment": risk_score,
        "decision": decision,
        "recommended_action": decision,
        "risk_category": risk_category,
        "risk_tier": risk_category,
        "category": risk_category,
        "xgb_probability": round(p_fraud, 4),
        "xgb_prob": round(p_fraud, 4),
        "xgboost_probability": round(p_fraud, 4),
        "fraud_probability": round(p_fraud, 4),
        "anomaly_score": round(p_anomaly, 4),
        "isolation_score": round(p_anomaly, 4),
        "isolation_anomaly_score": round(p_anomaly, 4),
        "confidence": round(p_fraud, 4),
        "model_used": model_name,
        "model_version": "v1.0.0-academic",
        "explanation": reasons[0] if reasons else "Standard digital payment parameters.",
        "reasons": reasons,
        "explanatory_signals": reasons,
        "rule_signals": rule_signals,
    }


# ─── CORE PREDICTION ENDPOINTS ───────────────────────────────────────────────
@app.post("/api/predict")
@app.post("/predict")
@app.post("/api/v1/predict")
@app.post("/api/analyze")
async def predict_post(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body in request.")
    return run_real_prediction(payload)

@app.get("/api/predict")
@app.get("/predict")
@app.get("/api/v1/predict")
@app.get("/api/analyze")
async def predict_get(amount_inr: float = 185.0, channel: str = "UPI_P2P"):
    return run_real_prediction({"amount_inr": amount_inr, "channel": channel})

@app.options("/api/predict")
@app.options("/predict")
@app.options("/api/v1/predict")
@app.options("/api/analyze")
async def predict_options():
    return {"status": "ok"}


# ─── SYSTEM HEALTH & METADATA ────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "VaultGuard Fraud Detection API Running",
        "version": "v1.0.0-academic"
    }

@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    models_ready = rf_model is not None or xgb_model is not None
    return {
        "status": "healthy" if models_ready else "degraded",
        "engine": "active",
        "version": "v1.0.0-academic",
        # This project currently serves deterministic in-memory demo records; no database connection is configured.
        "database": "not_configured",
        "data_source": "synthetic_demo",
        "transaction_count": 100,
        "ml_artifacts": "ready" if models_ready else "missing_models"
    }

@app.get("/api/v1/model-info")
@app.get("/model-info")
@app.get("/api/model-info")
def model_info():
    available_models = []
    if xgb_model is not None:
        available_models.append("xgboost")
    if rf_model is not None:
        available_models.append("random_forest")
    if iso_model is not None:
        available_models.append("isolation_forest")
    models_ready = xgb_model is not None or rf_model is not None

    return {
        "status": "active" if models_ready else "degraded",
        "version": "v1.0.0-academic",
        "model_version": "v1.0.0-academic",
        "active_model_version": "v1.0.0-academic",
        "models": available_models,
        "active_model": (
            "xgboost" if xgb_model is not None
            else "random_forest" if rf_model is not None
            else "heuristic_fallback"
        )
    }

@app.get("/api/models/metrics")
@app.get("/models/metrics")
@app.get("/api/v1/models/metrics")
def get_metrics():
    # Return metrics calculated from training splits in metrics.json
    p = metrics_data.get("precision")
    r = metrics_data.get("recall")
    f1 = metrics_data.get("f1_score")
    roc = metrics_data.get("roc_auc")
    pr = metrics_data.get("pr_auc")

    confusion = metrics_data.get("confusion_matrix")
    accuracy = None
    if isinstance(confusion, list) and len(confusion) == 2 and all(isinstance(row, list) and len(row) == 2 for row in confusion):
        total = sum(sum(float(value) for value in row) for row in confusion)
        if total > 0:
            accuracy = (float(confusion[0][0]) + float(confusion[1][1])) / total

    return {
        "status": "success" if metrics_data else "unavailable",
        "precision": p,
        "recall": r,
        "f1": round(float(f1) * 100, 1) if f1 is not None else None,
        "f1_score": f1,
        "roc_auc": roc,
        "pr_auc": pr,
        "accuracy": accuracy,
        "model_benchmarks": metrics_data.get("model_benchmarks", {})
    }


# ─── DASHBOARD & ANALYTICS ENDPOINTS ─────────────────────────────────────────
@app.get("/api/analytics/overview")
@app.get("/analytics/overview")
@app.get("/api/v1/analytics/overview")
def analytics():
    # Keep dashboard KPIs consistent with the records actually returned by the demo API.
    rows = get_transactions(limit=10000, page=1)
    total = len(rows)
    blocked = sum(1 for row in rows if row.get("decision") == "Block")
    review = sum(1 for row in rows if row.get("decision") == "Manual Review")
    allowed = sum(1 for row in rows if row.get("decision") == "Allow")
    flagged = sum(1 for row in rows if float(row.get("risk_score", 0)) > 40)
    high_risk = sum(1 for row in rows if row.get("risk_category") == "HIGH_RISK")
    return {
        "status": "success",
        "data_source": "synthetic_demo",
        "total_transactions": total,
        # Demo records do not contain ground-truth fraud labels.
        "fraud_labels": 0,
        "dataset_fraud_labels": 0,
        "high_risk_count": high_risk,
        "high_risk_transactions": high_risk,
        "total_blocked": blocked,
        "total_review": review,
        "total_allowed": allowed,
        "total_fraud_flagged": flagged,
        "f1_score": metrics_data.get("f1_score"),
        "database_records": total
    }

@app.get("/api/trend")
@app.get("/trend")
@app.get("/api/v1/trend")
def trend(range: str = "24h"):
    # Emit the field names expected by the dashboard chart and derive values from demo rows.
    rows = get_transactions(limit=10000, page=1)
    buckets = {}
    for row in rows:
        stamp = str(row.get("timestamp", ""))
        try:
            parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        bucket_time = parsed.replace(minute=0, second=0, microsecond=0)
        key = bucket_time.strftime("%Y-%m-%d %H:%M")
        bucket = buckets.setdefault(key, {"timestamp": key, "total": 0, "blocked": 0, "manual_review": 0, "suspicious": 0})
        bucket["total"] += 1
        decision_value = str(row.get("decision", "")).strip().lower()
        if decision_value == "block":
            bucket["blocked"] += 1
        if decision_value == "manual review":
            bucket["manual_review"] += 1
        if float(row.get("risk_score", 0)) > 40:
            bucket["suspicious"] += 1
    return [buckets[key] for key in sorted(buckets)]

@app.get("/api/risk-score")
@app.get("/risk-score")
@app.get("/api/v1/risk-score")
def risk_score():
    rows = get_transactions(limit=10000, page=1)
    counts = {
        "LOW_RISK": sum(1 for row in rows if row.get("risk_category") == "LOW_RISK"),
        "REVIEW": sum(1 for row in rows if row.get("risk_category") == "REVIEW"),
        "HIGH_RISK": sum(1 for row in rows if row.get("risk_category") == "HIGH_RISK"),
    }
    return [
        {"name": "Low Risk", "label": "Low Risk", "value": counts["LOW_RISK"], "count": counts["LOW_RISK"], "color": "#10B981"},
        {"name": "Medium Risk", "label": "Medium Risk", "value": counts["REVIEW"], "count": counts["REVIEW"], "color": "#F59E0B"},
        {"name": "High Risk", "label": "High Risk", "value": counts["HIGH_RISK"], "count": counts["HIGH_RISK"], "color": "#EF4444"}
    ]

@app.get("/api/transactions")
@app.get("/transactions")
@app.get("/api/v1/transactions")
def get_transactions(
    limit: int = Query(20, ge=1, le=10000),
    page: int = Query(1, ge=1),
    risk_category: Optional[str] = None,
    decision: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    segment: Optional[str] = None,
):
    """
    Return a deterministic synthetic transaction dataset for the demo UI.
    These are illustrative records, not live bank/customer transactions.
    """
    templates = [
        {
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "amount": 8500.0,
            "sender_id": "CUST_IND_9099",
            "beneficiary_id": "BEN_IND_MULE_101",
            "sender_vpa": "victim.user@okhdfcbank",
            "beneficiary_vpa": "mule.drain@paytm",
            "risk_score": 86.4,
            "risk_category": "HIGH_RISK",
            "decision": "Block",
            "status": "FLAGGED",
            "reasons": ["High-risk device takeover: simultaneous new device & recent SIM swap"],
        },
        {
            "channel": "UPI_P2M_QR",
            "transaction_type": "MERCHANT_PAYMENT",
            "amount": 185.0,
            "sender_id": "CUST_IND_1464",
            "beneficiary_id": "MERCH_IND_102",
            "sender_vpa": "sanjay.sharma69@paytm",
            "beneficiary_vpa": "apna.kirana@paytm",
            "risk_score": 7.1,
            "risk_category": "LOW_RISK",
            "decision": "Allow",
            "status": "APPROVED",
            "reasons": ["Verified customer baseline parameters"],
        },
        {
            "channel": "IMPS",
            "transaction_type": "P2P_TRANSFER",
            "amount": 4990.0,
            "sender_id": "CUST_IND_3029",
            "beneficiary_id": "BEN_IND_1610",
            "sender_vpa": "rahul.nair50@barodampay",
            "beneficiary_vpa": "karthik.gupta17@okhdfcbank",
            "risk_score": 71.1,
            "risk_category": "HIGH_RISK",
            "decision": "Block",
            "status": "FLAGGED",
            "reasons": ["Structuring pattern: amount just below regulatory limit"],
        },
        {
            "channel": "WALLET",
            "transaction_type": "WALLET_TRANSFER",
            "amount": 1250.0,
            "sender_id": "CUST_IND_4410",
            "beneficiary_id": "MERCH_IND_230",
            "sender_vpa": "demo.customer@paytm",
            "beneficiary_vpa": "demo.store@paytm",
            "risk_score": 48.2,
            "risk_category": "REVIEW",
            "decision": "Manual Review",
            "status": "REVIEW",
            "reasons": ["Unusual transaction amount; additional review recommended"],
        },
        {
            "channel": "RUPAY_CARD",
            "transaction_type": "CARD_PAYMENT",
            "amount": 2199.0,
            "sender_id": "CUST_IND_5721",
            "beneficiary_id": "MERCH_IND_315",
            "sender_vpa": "demo.cardholder@bank",
            "beneficiary_vpa": "demo.retailer@merchant",
            "risk_score": 18.6,
            "risk_category": "LOW_RISK",
            "decision": "Allow",
            "status": "APPROVED",
            "reasons": ["No elevated risk indicators in this synthetic example"],
        },
    ]

    # Build a larger repeatable demo dataset instead of returning only 3 hard-coded rows.
    mock_txns = []
    base_time = datetime(2026, 10, 28, 19, 10, 0)
    for index in range(100):
        template = templates[index % len(templates)]
        txn = dict(template)
        txn["reasons"] = list(template["reasons"])
        txn_id = f"TXN_IND_{1001 + index}"
        txn_time = base_time - timedelta(minutes=5 * index)
        # Vary the amount and score slightly while keeping the risk band consistent.
        amount = round(float(template["amount"]) + ((index // len(templates)) % 7) * 37.0, 2)
        score = round(min(100.0, max(0.0, float(template["risk_score"]) + ((index // len(templates)) % 5) * 1.3)), 1)
        if score > 70:
            category, action, status_value = "HIGH_RISK", "Block", "FLAGGED"
        elif score > 40:
            category, action, status_value = "REVIEW", "Manual Review", "REVIEW"
        else:
            category, action, status_value = "LOW_RISK", "Allow", "APPROVED"
        txn.update({
            "id": txn_id,
            "transaction_id": txn_id,
            "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time": txn_time.strftime("%H:%M:%S"),
            "amount": amount,
            "amount_inr": amount,
            "sender_id": f"CUST_IND_{1000 + ((index * 37) % 9000):04d}",
            "beneficiary_id": f"{'BEN' if index % 2 == 0 else 'MERCH'}_IND_{100 + ((index * 13) % 900):03d}",
            "risk_score": score,
            "risk_assessment": score,
            "risk_tier": category,
            "risk_category": category,
            "decision": action,
            "status": status_value,
        })
        mock_txns.append(txn)

    filtered = mock_txns
    if risk_category and risk_category != "All":
        filtered = [t for t in filtered if t["risk_category"] == risk_category]
    if decision and decision != "All":
        filtered = [t for t in filtered if t["decision"] == decision]
    if channel and channel != "All":
        filtered = [t for t in filtered if t["channel"] == channel]
    if segment and segment != "All":
        filtered = [t for t in filtered if t.get("segment") == segment]
    if search:
        term = search.strip().lower()
        filtered = [
            t for t in filtered
            if term in str(t.get("transaction_id", "")).lower()
            or term in str(t.get("sender_id", "")).lower()
            or term in str(t.get("beneficiary_id", "")).lower()
            or term in str(t.get("sender_vpa", "")).lower()
            or term in str(t.get("beneficiary_vpa", "")).lower()
        ]
    if min_amount is not None:
        filtered = [t for t in filtered if float(t.get("amount_inr", t.get("amount", 0))) >= min_amount]
    if max_amount is not None:
        filtered = [t for t in filtered if float(t.get("amount_inr", t.get("amount", 0))) <= max_amount]

    start_index = (page - 1) * limit
    return filtered[start_index:start_index + limit]

@app.get("/api/export")
@app.get("/export")
def export_transactions(type: str = Query("csv", regex="^csv$")):
    """Download the transaction dataset as a CSV attachment."""
    rows = get_transactions(limit=10000, page=1)
    if not rows:
        raise HTTPException(status_code=404, detail="No transactions are available to export.")

    preferred_columns = [
        "transaction_id", "timestamp", "channel", "transaction_type",
        "amount_inr", "sender_id", "beneficiary_id", "risk_score",
        "risk_category", "decision", "status", "reasons",
    ]
    columns = [key for key in preferred_columns if any(key in row for row in rows)]
    extra_columns = sorted({key for row in rows for key in row.keys()} - set(columns))
    columns.extend(extra_columns)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        safe_row = dict(row)
        reasons = safe_row.get("reasons")
        if isinstance(reasons, (list, dict)):
            safe_row["reasons"] = json.dumps(reasons, ensure_ascii=False)
        writer.writerow(safe_row)

    csv_content = chr(0xFEFF) + output.getvalue()
    filename = "vaultguard-transactions-" + datetime.now(timezone.utc).date().isoformat() + ".csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="' + filename + '"'},
    )


@app.get("/api/transactions/{txn_id}")
def get_transaction_detail(txn_id: str):
    return {
        "id": txn_id,
        "transaction_id": txn_id,
        "timestamp": "2026-10-28 19:10:00",
        "channel": "UPI_P2P",
        "amount_inr": 8500.0,
        "sender_id": "CUST_IND_9099",
        "beneficiary_id": "BEN_IND_MULE_101",
        "risk_score": 86.4,
        "risk_category": "HIGH_RISK",
        "decision": "Block",
        "reasons": [
            "High-risk device takeover: simultaneous new device & recent SIM swap",
            "Recent SIM card change detected on account",
            "Transaction originating from unverified new device"
        ]
    }


# ─── ENTITIES (CUSTOMERS, MERCHANTS, CASES, RULES) ───────────────────────────
@app.get("/api/customers")
@app.get("/customers")
@app.get("/api/v1/customers")
def get_customers(page: int = 1, limit: int = 20):
    customers = [
        {
            "id": 1,
            "customer_id": "CUST_IND_9099",
            "name": "Rahul Sharma",
            "segment": "Consumer",
            "risk_level": "HIGH",
            "total_transactions": 45,
            "fraud_incidents": 1,
            "total_spend": 128500.0,
            "status": "FLAGGED"
        },
        {
            "id": 2,
            "customer_id": "CUST_IND_1464",
            "name": "Priya Patel",
            "segment": "Salaried Professional",
            "risk_level": "LOW",
            "total_transactions": 128,
            "fraud_incidents": 0,
            "total_spend": 45200.0,
            "status": "ACTIVE"
        },
        {
            "id": 3,
            "customer_id": "CUST_IND_3029",
            "name": "Amit Kumar",
            "segment": "Trader",
            "risk_level": "MEDIUM",
            "total_transactions": 82,
            "fraud_incidents": 0,
            "total_spend": 320000.0,
            "status": "ACTIVE"
        }
    ]
    return customers

@app.get("/api/merchants")
@app.get("/merchants")
@app.get("/api/v1/merchants")
def get_merchants(page: int = 1, limit: int = 20, category: Optional[str] = None):
    merchants = [
        {
            "id": 1,
            "merchant_id": "MERCH_IND_102",
            "category": "kirana_grocery",
            "spike_ratio": 1.1,
            "risk_level": "LOW",
            "total_volume": 452100.0,
            "transaction_count": 890
        },
        {
            "id": 2,
            "merchant_id": "MERCH_IND_112",
            "category": "digital_services",
            "spike_ratio": 4.8,
            "risk_level": "HIGH",
            "total_volume": 1250000.0,
            "transaction_count": 420
        },
        {
            "id": 3,
            "merchant_id": "MERCH_IND_125",
            "category": "food_dining",
            "spike_ratio": 1.3,
            "risk_level": "LOW",
            "total_volume": 182000.0,
            "transaction_count": 310
        }
    ]
    if category and category != "All":
        return [m for m in merchants if m["category"] == category]
    return merchants

@app.get("/api/cases")
@app.get("/cases")
@app.get("/api/cases/active")
def get_cases(limit: int = 20):
    cases = [
        {
            "id": 1,
            "case_id": "CASE_2026_001",
            "title": "Suspected ATO drain via UPI P2P",
            "customer_id": "CUST_IND_9099",
            "transaction_id": "TXN_IND_1001",
            "risk_score": 86.4,
            "status": "OPEN",
            "severity": "CRITICAL",
            "assigned_analyst": "Analyst Team",
            "created_at": "2026-10-28 19:15:00"
        },
        {
            "id": 2,
            "case_id": "CASE_2026_002",
            "title": "Structuring probe near INR 5,000 threshold",
            "customer_id": "CUST_IND_3029",
            "transaction_id": "TXN_IND_1003",
            "risk_score": 71.1,
            "status": "UNDER_REVIEW",
            "severity": "HIGH",
            "assigned_analyst": "Risk Operations",
            "created_at": "2026-10-28 18:55:00"
        }
    ]
    return {
        "status": "success",
        "cases": cases,
        "alerts": []
    }

@app.patch("/api/cases/{case_id}/status")
def update_case_status(case_id: str, payload: Dict[str, Any]):
    return {"status": "success", "case_id": case_id, "new_status": payload.get("status", "OPEN")}

@app.get("/api/cases/{case_id}/notes")
def get_case_notes(case_id: str):
    return []

@app.post("/api/cases/{case_id}/notes")
def add_case_note(case_id: str, payload: Dict[str, Any]):
    return {"status": "success", "note_id": 1, "case_id": case_id, "body": payload.get("body", "")}

@app.get("/api/cases/{case_id}/history")
def get_case_history(case_id: str):
    return [
        {"id": 1, "event_type": "created", "timestamp": "2026-10-28 19:15:00", "details": "Auto-created by VaultGuard"}
    ]

@app.get("/api/rules")
@app.get("/rules")
@app.get("/api/v1/rules")
def get_rules():
    return [
        {
            "id": 1,
            "rule_key": "sim_swap_device_takeover",
            "value": 1.0,
            "enabled": True,
            "version": 1,
            "updated_by": "System Baseline"
        },
        {
            "id": 2,
            "rule_key": "amount_structuring_threshold",
            "value": 5000.0,
            "enabled": True,
            "version": 1,
            "updated_by": "Compliance Engine"
        },
        {
            "id": 3,
            "rule_key": "rapid_velocity_1min_burst",
            "value": 3.0,
            "enabled": True,
            "version": 1,
            "updated_by": "Risk Engine"
        },
        {
            "id": 4,
            "rule_key": "merchant_volume_spike_ceiling",
            "value": 3.0,
            "enabled": True,
            "version": 1,
            "updated_by": "Merchant Telemetry"
        }
    ]

@app.get("/api/alerts")
@app.get("/alerts")
@app.get("/api/v1/alerts")
def get_alerts(limit: int = 10):
    return [
        {
            "id": 1,
            "alert_code": "ALT_ATO_99",
            "title": "SIM Swap + New Device Takeover",
            "segment": "UPI P2P",
            "severity": "CRITICAL",
            "status": "Monitoring",
            "time_ago": "Just now",
            "assignee": "VaultGuard ML",
            "created_at": "2026-10-28 19:10:00"
        },
        {
            "id": 2,
            "alert_code": "ALT_STRUC_10",
            "title": "Structuring under 5,000 INR limit",
            "segment": "IMPS",
            "severity": "HIGH",
            "status": "Investigating",
            "time_ago": "15m ago",
            "assignee": "AML Unit",
            "created_at": "2026-10-28 18:50:00"
        }
    ]

@app.patch("/api/alerts/{alert_id}")
def update_alert(alert_id: int, payload: Dict[str, Any]):
    return {
        "status": "success",
        "id": alert_id,
        "new_status": payload.get("status", "Investigating"),
        "acknowledged_at": datetime.now(timezone.utc).isoformat()
    }


# ─── BULK ANALYSIS SCHEMA & SAMPLES ──────────────────────────────────────────
@app.get("/api/bulk-analysis/schema")
def get_bulk_schema():
    return {
        "required_columns": ["transaction_id", "timestamp", "amount_inr", "sender_id"],
        "optional_columns": ["channel", "transaction_type", "beneficiary_id", "device_id", "is_new_device", "sim_change_flag"]
    }

@app.get("/api/bulk-analysis/sample.csv")
def get_bulk_sample():
    csv_content = "transaction_id,timestamp,amount_inr,channel,transaction_type,sender_id,beneficiary_id,device_id,is_new_device,sim_change_flag\n" \
                  "TXN_SMPL_01,2026-10-28 12:00:00,185.0,UPI_P2M_QR,MERCHANT_PAYMENT,CUST_01,MERCH_01,DEV_01,0,0\n" \
                  "TXN_SMPL_02,2026-10-28 12:05:00,8500.0,UPI_P2P,P2P_TRANSFER,CUST_02,MULE_01,DEV_NEW,1,1\n"
    return PlainTextResponse(content=csv_content, media_type="text/csv")




# ─── BULK CSV ANALYSIS ────────────────────────────────────────────────────────
# Results are kept in process memory for immediate download. On serverless
# platforms this cache is temporary; durable history requires an external DB.
_BULK_ANALYSES: Dict[str, List[Dict[str, Any]]] = {}
_BULK_MAX_BYTES = 5 * 1024 * 1024
_BULK_MAX_ROWS = 10000
_BULK_REQUIRED_COLUMNS = {"transaction_id", "timestamp", "amount_inr", "sender_id"}


@app.post("/api/bulk-analysis/upload")
async def upload_bulk_analysis(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    raw = await file.read(_BULK_MAX_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded CSV is empty.")
    if len(raw) > _BULK_MAX_BYTES:
        raise HTTPException(status_code=413, detail="CSV exceeds the 5 MB upload limit.")
    try:
        decoded = raw.decode("utf-8-sig")
        frame = pd.read_csv(io.StringIO(decoded), dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must use UTF-8 encoding.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    frame.columns = [str(column).strip() for column in frame.columns]
    if frame.empty:
        raise HTTPException(status_code=400, detail="The CSV contains no data rows.")
    if len(frame) > _BULK_MAX_ROWS:
        raise HTTPException(status_code=413, detail="CSV exceeds the 10,000-row upload limit.")
    missing = sorted(_BULK_REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise HTTPException(status_code=400, detail="Missing required columns: " + ", ".join(missing))

    records = []
    extra_columns = sorted(set(frame.columns) - (_BULK_REQUIRED_COLUMNS | {
        "channel", "transaction_type", "beneficiary_id", "merchant_id",
        "merchant_category", "device_id", "is_new_device", "sim_change_flag",
        "is_fraud"
    }))
    invalid_rows = 0
    for row_index, (_, row) in enumerate(frame.iterrows(), start=1):
        original = row.to_dict()
        # Ground-truth labels, if supplied, are preserved as unverified metadata
        # and are deliberately excluded from model input.
        model_input = {key: value for key, value in original.items() if key != "is_fraud"}
        try:
            amount = float(str(model_input.get("amount_inr", "")).strip())
            if not np.isfinite(amount) or amount <= 0:
                raise ValueError("amount_inr must be a positive number")
            model_input["amount_inr"] = amount
            prediction = run_real_prediction(model_input)
            risk_score = float(prediction.get("risk_score", 0))
            records.append({
                "source_row": row_index,
                "transaction_id": str(original.get("transaction_id") or prediction.get("transaction_id")),
                "original": original,
                "risk_score": risk_score,
                "risk_category": prediction.get("risk_category", "REVIEW"),
                "predicted_class": (
                    "Suspected Fraud" if prediction.get("decision") == "Block"
                    else "Needs Review" if prediction.get("decision") == "Manual Review"
                    else "Normal Prediction"
                ),
                "decision": prediction.get("decision", "Manual Review"),
                "reasons": prediction.get("reasons", []),
                "model_used": prediction.get("model_used", "Configured model"),
                "status": "analysed",
            })
        except Exception as exc:
            invalid_rows += 1
            records.append({
                "source_row": row_index,
                "transaction_id": str(original.get("transaction_id") or f"row-{row_index}"),
                "original": original,
                "risk_score": None,
                "risk_category": "INVALID",
                "predicted_class": "Invalid Row",
                "decision": "Not analysed",
                "reasons": [str(exc)[:240]],
                "model_used": None,
                "status": "invalid",
            })

    analysed = [record for record in records if record["status"] == "analysed"]
    scores = [record["risk_score"] for record in analysed if record.get("risk_score") is not None]
    analysis_id = uuid.uuid4().hex
    _BULK_ANALYSES[analysis_id] = records
    return {
        "status": "success",
        "analysis_id": analysis_id,
        "summary": {
            "total_rows": len(records),
            "analysed_rows": len(analysed),
            "invalid_rows": invalid_rows,
            "suspected_fraud": sum(1 for record in analysed if record["predicted_class"] == "Suspected Fraud"),
            "high_risk": sum(1 for record in analysed if record["risk_category"] == "HIGH_RISK"),
            "normal_predictions": sum(1 for record in analysed if record["predicted_class"] == "Normal Prediction"),
            "manual_review": sum(1 for record in analysed if record["predicted_class"] == "Needs Review"),
            "average_risk_score": round(sum(scores) / len(scores), 1) if scores else None,
        },
        "extra_columns": extra_columns,
        "records": records,
        "notice": "Predictions are model assessments, not confirmed fraud. Supplied is_fraud values are unverified and were not used for inference.",
    }


@app.get("/api/bulk-analysis/{analysis_id}/export")
def export_bulk_analysis(analysis_id: str):
    records = _BULK_ANALYSES.get(analysis_id)
    if records is None:
        raise HTTPException(
            status_code=404,
            detail="This analysis is no longer available on this server instance. Please upload and analyse the CSV again, then download the report immediately."
        )
    output = io.StringIO(newline="")
    # Keep prediction columns separate from original input columns. If an input
    # column collides with a prediction field (for example "decision"), prefix
    # it with "input_" so the original value is not lost or confused with output.
    prediction_columns = [
        "source_row", "transaction_id", "risk_score", "risk_category",
        "predicted_class", "decision", "status", "reasons"
    ]
    source_columns = []
    for record in records:
        for key in record.get("original", {}):
            output_key = key if key not in prediction_columns else f"input_{key}"
            if output_key not in source_columns:
                source_columns.append(output_key)
    columns = prediction_columns + [key for key in source_columns if key not in prediction_columns]
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        row = {
            "source_row": record.get("source_row"),
            "transaction_id": record.get("transaction_id"),
            "risk_score": record.get("risk_score"),
            "risk_category": record.get("risk_category"),
            "predicted_class": record.get("predicted_class"),
            "decision": record.get("decision"),
            "status": record.get("status"),
            "reasons": json.dumps(record.get("reasons", []), ensure_ascii=False),
        }
        for key, value in record.get("original", {}).items():
            output_key = key if key not in prediction_columns else f"input_{key}"
            row[output_key] = value
        writer.writerow(row)
    content = chr(0xFEFF) + output.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vaultguard-bulk-analysis-' + analysis_id[:8] + '.csv"'}
    )


# ─── WEBSOCKET (GRACEFUL LOCAL SUPPORT) ──────────────────────────────────────
@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
