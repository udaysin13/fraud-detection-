"""
VaultGuard - Unit Tests for Feature Engineering & Model Scoring
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from ml.features import engineer_features, check_just_below_threshold
from ml.predict import score_transaction, get_decision


def test_just_below_threshold_check():
    assert check_just_below_threshold(9.50) == 1
    assert check_just_below_threshold(49.90) == 1
    assert check_just_below_threshold(99.00) == 1
    assert check_just_below_threshold(25.00) == 0


def test_decision_thresholds():
    assert get_decision(20.0) == "Allow"
    assert get_decision(40.0) == "Allow"
    assert get_decision(55.0) == "Manual Review"
    assert get_decision(70.0) == "Manual Review"
    assert get_decision(85.0) == "Block"


def test_feature_engineering():
    sample_df = pd.DataFrame([
        {
            "transaction_id": "TXN_TEST_001",
            "timestamp": "2026-09-23 12:00:00",
            "card_id": "CARD_100",
            "customer_id": "CUST_100",
            "merchant_id": "MERCH_100",
            "merchant_category": "digital_goods",
            "amount": 2.50,
            "currency": "USD",
            "country": "US",
            "billing_country": "RU",
            "device_id": "DEV_100",
            "ip_address": "1.1.1.1",
            "is_new_device": 1,
            "bin_range": "499999",
            "channel": "web",
            "segment": "AS Cards",
            "is_fraud": 1,
        }
    ])

    X_df, feature_names = engineer_features(sample_df)
    assert not X_df.empty
    assert "geo_mismatch" in X_df.columns
    assert X_df["geo_mismatch"].iloc[0] == 1
    assert X_df["high_risk_bin"].iloc[0] == 1


def test_score_transaction():
    sample_txn = {
        "transaction_id": "TXN_SCORE_TEST",
        "timestamp": "2026-09-23 12:00:00",
        "card_id": "CARD_SCORE_100",
        "customer_id": "CUST_SCORE_100",
        "merchant_id": "MERCH_100",
        "merchant_category": "digital_goods",
        "amount": 2.50,
        "currency": "USD",
        "country": "US",
        "billing_country": "RU",
        "device_id": "DEV_SCORE_100",
        "ip_address": "1.1.1.1",
        "is_new_device": 1,
        "bin_range": "499999",
        "channel": "web",
        "segment": "AS Cards",
    }

    result = score_transaction(sample_txn)
    assert "risk_score" in result
    assert "decision" in result
    assert "reasons" in result
    assert isinstance(result["risk_score"], float)
    assert result["decision"] in ["Allow", "Manual Review", "Block"]
    assert len(result["reasons"]) == 3
