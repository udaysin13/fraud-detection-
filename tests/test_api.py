"""
VaultGuard - Comprehensive Integration Tests for FastAPI Endpoints (Phase 4)
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routes.analytics import get_fraud_trend, get_risk_score_summary

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["database"] == "connected"
    assert data["ml_artifacts"] == "ready"
    assert "transaction_count" in data


def test_analytics_overview():
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_transactions" in data
    assert "dataset_fraud_labels" in data
    assert "total_fraud_flagged" in data
    assert "total_blocked" in data
    assert "total_review" in data
    assert "total_allowed" in data
    assert "fraud_rate_pct" in data
    assert "avg_risk_score" in data


def test_risk_score_endpoint():
    response = client.get("/api/risk-score")
    assert response.status_code == 200
    data = response.json()
    assert "flagged_count" in data
    assert "top_contributors" in data
    assert isinstance(data["flagged_count"], int)
    assert isinstance(data["top_contributors"], list)


def test_trend_endpoint():
    for r in ["24h", "7d", "30d"]:
        response = client.get(f"/api/trend?range={r}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def test_trend_range_excludes_older_transactions():
    now = datetime.now(timezone.utc)
    recent = now.strftime("%Y-%m-%d %H:%M:%S")
    older = (now - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")

    class Query:
        def order_by(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def all(self):
            return [(recent, 80.0, "Block"), (older, 90.0, "Block")]

    class EmptyHistoryDB:
        def query(self, *_args):
            return Query()

    trend = get_fraud_trend(range="24h", db=EmptyHistoryDB())
    assert len(trend) == 1
    assert trend[0]["blocked"] == 1


def test_risk_summary_does_not_invent_empty_contributors():
    class EmptyQuery:
        def filter(self, *_args):
            return self

        def order_by(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def count(self):
            return 0

        def all(self):
            return []

    class EmptyHistoryDB:
        def query(self, *_args):
            return EmptyQuery()

    summary = get_risk_score_summary(db=EmptyHistoryDB())
    assert summary["flagged_count"] == 0
    assert summary["top_contributors"] == []


def test_alerts_endpoints():
    # GET alerts
    get_res = client.get("/api/alerts")
    assert get_res.status_code == 200
    alerts = get_res.json()
    assert isinstance(alerts, list)

    # POST new alert
    new_alert_code = f"ALT-TEST-{int(time.time() * 1000)}"
    post_res = client.post(
        "/api/alerts",
        json={
            "alert_code": new_alert_code,
            "title": "Test Alert Creation",
            "segment": "UPI Payments",
            "time_ago": "1 min ago",
            "status": "Monitoring",
            "assignee": "Aarav Sharma",
        },
    )
    assert post_res.status_code == 201
    created = post_res.json()
    assert created["alert_code"] == new_alert_code

    # PATCH alert
    alert_id = created["id"]
    patch_res = client.patch(
        f"/api/alerts/{alert_id}",
        json={"status": "Resolved", "assignee": "Priya Nair"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "Resolved"
    assert updated["assignee"] == "Priya Nair"


def test_transactions_endpoints():
    # Paginated listing
    response = client.get("/api/transactions?limit=5&page=1")
    assert response.status_code == 200
    txns = response.json()
    assert isinstance(txns, list)

    # Filter by decision
    allow_res = client.get("/api/transactions?decision=Allow&limit=2")
    assert allow_res.status_code == 200

    # Search filter
    search_res = client.get("/api/transactions?search=TXN&limit=2")
    assert search_res.status_code == 200


def test_predict_endpoint_indian_upi():
    """Tests prediction with Indian digital payment payload (UPI, SIM change flag, etc.)."""
    unique_id = f"TXN_IND_TEST_{int(time.time() * 1000)}"
    payload = {
        "transaction_id": unique_id,
        "amount_inr": 8200.0,
        "channel": "UPI_P2P",
        "transaction_type": "P2P_TRANSFER",
        "sender_id": "CUST_IND_9099",
        "beneficiary_id": "BEN_IND_3021",
        "sender_vpa": "victim.user@okhdfcbank",
        "beneficiary_vpa": "mule.account@paytm",
        "device_id": "DEV_IND_9999",
        "is_new_device": 1,
        "sim_change_flag": 1,  # Critical ATO indicator
        "ip_location_state": "Maharashtra",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == unique_id
    assert "risk_score" in data
    assert data["risk_score"] > 60.0  # SIM change + new device + high amount should trigger high risk
    assert data["decision"] in ["Block", "Manual Review"]
    assert "risk_category" in data
    assert len(data["reasons"]) > 0

    # Verify transaction can be retrieved via GET /api/transactions/{transaction_id}
    detail_res = client.get(f"/api/transactions/{unique_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["transaction_id"] == unique_id
    assert detail["amount_inr"] == 8200.0


def test_predict_endpoint_legacy_compat():
    """Tests backward-compatible prediction using legacy fields sent by current React UI."""
    unique_id = f"TXN_LEGACY_TEST_{int(time.time() * 1000)}"
    payload = {
        "transaction_id": unique_id,
        "card_id": "CARD_API_100",
        "customer_id": "CUST_API_100",
        "merchant_id": "MERCH_100",
        "merchant_category": "digital_goods",
        "amount": 3.25,
        "currency": "USD",
        "country": "US",
        "billing_country": "RU",
        "device_id": "DEV_API_100",
        "ip_address": "1.1.1.1",
        "is_new_device": 1,
        "bin_range": "499999",
        "channel": "web",
        "segment": "AS Cards",
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "decision" in data
    assert "reasons" in data
    assert "xgb_probability" in data
    assert "anomaly_score" in data


def test_entities_endpoints():
    cust_res = client.get("/api/customers?limit=5")
    assert cust_res.status_code == 200

    merch_res = client.get("/api/merchants?limit=5")
    assert merch_res.status_code == 200

    cases_res = client.get("/api/cases?limit=5")
    assert cases_res.status_code == 200


def test_model_metrics_endpoint():
    response = client.get("/api/models/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "precision" in data
    assert "recall" in data
    assert "f1_score" in data
    assert "roc_auc" in data
    assert data["precision"] > 0.90
    assert data["recall"] > 0.90
