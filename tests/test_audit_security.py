"""
VaultGuard - Phase 6 QA, Security & ML Reliability Regression Tests
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routes.analytics import sanitize_csv_cell
from backend.app.database import SessionLocal
from backend.app.models.orm import TransactionORM
from ml.predict import get_decision, get_risk_category, score_transaction
from ml.features import FEATURE_COLUMNS, engineer_features
import pandas as pd

client = TestClient(app)


# ─── 1. CSV Formula Injection Sanitization Tests (CWE-1236) ───────────────────

def test_sanitize_csv_cell_formula_injection():
    """Verifies that malicious spreadsheet formulas are neutralized."""
    malicious_inputs = [
        "=cmd|'/C calc'!A0",
        "+1+2",
        "-5+10",
        "@SUM(A1:A10)",
        "\t=2+3",
        "\r=1+1",
    ]
    for inp in malicious_inputs:
        sanitized = sanitize_csv_cell(inp)
        assert sanitized.startswith("'"), f"Failed to neutralize formula injection on: {inp}"

    # Benign inputs should remain untouched
    assert sanitize_csv_cell("TXN_12345") == "TXN_12345"
    assert sanitize_csv_cell("Aarav Sharma") == "Aarav Sharma"
    assert sanitize_csv_cell(None) == ""
    assert sanitize_csv_cell(125.50) == "125.5"


def test_export_endpoint_returns_sanitized_csv():
    """Verifies GET /api/export returns a valid CSV stream with proper headers."""
    response = client.get("/api/export?type=csv")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=" in response.headers["Content-Disposition"]
    content = response.text
    assert "transaction_id,timestamp,channel" in content


# ─── 2. Payload Validation & Boundary Tests ───────────────────────────────────

def test_predict_rejects_negative_amount():
    """Negative transaction amount must be rejected with HTTP 422."""
    payload = {
        "amount_inr": -50.0,
        "channel": "UPI_P2P",
        "sender_id": "CUST_TEST",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_rejects_excessive_amount():
    """Amount exceeding maximum limit (> 1 Crore) must be rejected with HTTP 422."""
    payload = {
        "amount_inr": 100_000_001.0,
        "channel": "UPI_P2P",
        "sender_id": "CUST_TEST",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_handles_unknown_channel_gracefully():
    """Unknown or malformed channel name should safely default without crashing."""
    payload = {
        "amount_inr": 150.0,
        "channel": "MALICIOUS_CHANNEL_NAME_123",
        "sender_id": "CUST_TEST",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data


def test_predict_rejects_oversized_string_fields():
    """Oversized fields (> 128/256 chars) must be rejected with HTTP 422 to prevent DoS."""
    payload = {
        "amount_inr": 200.0,
        "sender_id": "X" * 300,  # Max length is 128
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


# ─── 3. Decision & Threshold Boundary Tests ───────────────────────────────────

def test_decision_and_risk_category_boundaries():
    """
    Verifies precise mathematical threshold boundaries:
    - 0.0 to 40.0: Allow / LOW_RISK
    - 40.1 to 70.0: Manual Review / REVIEW
    - 70.1 to 100.0: Block / HIGH_RISK
    """
    # Low Risk boundaries
    assert get_decision(0.0) == "Allow"
    assert get_risk_category(0.0) == "LOW_RISK"
    assert get_decision(40.0) == "Allow"
    assert get_risk_category(40.0) == "LOW_RISK"

    # Review boundaries
    assert get_decision(40.1) == "Manual Review"
    assert get_risk_category(40.1) == "REVIEW"
    assert get_decision(70.0) == "Manual Review"
    assert get_risk_category(70.0) == "REVIEW"

    # High Risk boundaries
    assert get_decision(70.1) == "Block"
    assert get_risk_category(70.1) == "HIGH_RISK"
    assert get_decision(100.0) == "Block"
    assert get_risk_category(100.0) == "HIGH_RISK"


# ─── 4. ML Edge Cases & Missing Context Scoring ───────────────────────────────

def test_scoring_unseen_customer_without_history():
    """An entirely new user with zero prior transactions scores cleanly."""
    fresh_txn = {
        "transaction_id": f"TXN_FRESH_{int(time.time() * 1000)}",
        "timestamp": "2026-10-13 14:00:00",
        "amount_inr": 250.0,
        "channel": "UPI_P2P",
        "sender_id": "CUST_NEVER_SEEN_BEFORE_999",
        "beneficiary_id": "BEN_NEW_123",
        "is_new_device": 0,
        "sim_change_flag": 0,
    }
    res = score_transaction(fresh_txn)
    assert "risk_score" in res
    assert 0.0 <= res["risk_score"] <= 100.0
    assert res["decision"] in ["Allow", "Manual Review", "Block"]
    assert len(res["reasons"]) == 3


def test_scoring_zero_amount_edge_case():
    """Zero amount transaction is evaluated cleanly."""
    zero_txn = {
        "transaction_id": "TXN_ZERO_AMT",
        "timestamp": "2026-10-13 14:05:00",
        "amount_inr": 0.0,
        "channel": "UPI_P2M_QR",
        "sender_id": "CUST_ZERO",
    }
    res = score_transaction(zero_txn)
    assert "risk_score" in res
    assert 0.0 <= res["risk_score"] <= 100.0


def test_is_fraud_is_never_a_model_feature():
    """Confirms label columns are strictly excluded from engineered feature columns."""
    assert "is_fraud" not in FEATURE_COLUMNS
    assert "fraud_pattern" not in FEATURE_COLUMNS
    assert "pattern" not in FEATURE_COLUMNS
    assert "transaction_id" not in FEATURE_COLUMNS


# ─── 5. Administrative Endpoint Protection ────────────────────────────────────

def test_retrain_endpoint_admin_token_enforcement(monkeypatch):
    """
    When VAULTGUARD_ADMIN_TOKEN is configured in environment,
    unauthorized requests must be rejected with HTTP 401.
    """
    secret_token = "SECURE_ADMIN_SECRET_KEY_9988"
    monkeypatch.setenv("VAULTGUARD_ADMIN_TOKEN", secret_token)

    # 1. Missing header -> 401
    res_no_token = client.post("/api/models/retrain")
    assert res_no_token.status_code == 401

    # 2. Invalid header -> 401
    res_bad_token = client.post(
        "/api/models/retrain", headers={"X-Admin-Token": "WRONG_TOKEN"}
    )
    assert res_bad_token.status_code == 401
