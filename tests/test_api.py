"""
VaultGuard - Integration Tests for FastAPI Endpoints
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data


def test_risk_score_endpoint():
    response = client.get("/api/risk-score")
    assert response.status_code == 200
    data = response.json()
    assert "flagged_count" in data
    assert "top_contributors" in data
    assert isinstance(data["flagged_count"], int)


def test_trend_endpoint():
    response = client.get("/api/trend?range=24h")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_alerts_endpoints():
    # GET alerts
    get_res = client.get("/api/alerts")
    assert get_res.status_code == 200
    alerts = get_res.json()
    assert isinstance(alerts, list)

    # POST new alert
    new_alert_code = f"ALT-TEST-{int(pytest.importorskip('time').time())}"
    post_res = client.post(
        "/api/alerts",
        json={
            "alert_code": new_alert_code,
            "title": "Test Alert Creation",
            "segment": "APAC Cards",
            "time_ago": "1 min ago",
            "status": "Monitoring",
            "assignee": "John Lee",
        },
    )
    assert post_res.status_code == 201
    created = post_res.json()
    assert created["alert_code"] == new_alert_code


def test_transactions_endpoint():
    response = client.get("/api/transactions?limit=5")
    assert response.status_code == 200
    txns = response.json()
    assert isinstance(txns, list)


def test_predict_endpoint():
    import time
    unique_id = f"TXN_API_TEST_{int(time.time() * 1000)}"
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


def test_entities_endpoints():
    # Customers
    cust_res = client.get("/api/customers?limit=5")
    assert cust_res.status_code == 200

    # Merchants
    merch_res = client.get("/api/merchants?limit=5")
    assert merch_res.status_code == 200

    # Cases
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
