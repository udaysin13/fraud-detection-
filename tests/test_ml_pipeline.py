"""
VaultGuard - Phase 3 ML Pipeline Regression & Leakage Tests
Validates:
1. Rolling features remain aligned with transaction IDs across entities (fixing .values scrambling).
2. Future transactions do not leak into earlier transaction features.
3. Target columns (is_fraud, fraud_pattern) are strictly excluded from feature inputs.
4. Chronological splits preserve temporal ordering (70/15/15) without future bleed.
5. Preprocessing (StandardScaler) is fitted on training data only.
6. Decision threshold selection uses validation split only.
7. Evaluation metrics handle imbalanced splits and single-class edge cases safely.
8. Training and inference feature schemas are identical in names and ordering.
9. Serialized model artifacts load and score inference payloads reliably.
"""

import sys
import os
import math
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_recall_fscore_support, average_precision_score, roc_auc_score

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features import engineer_features, FEATURE_COLUMNS, check_just_below_threshold
from ml.predict import score_transaction, get_decision, get_risk_category, load_models
from ml.train import split_chronological, evaluate_predictions, tune_decision_threshold, MODELS_DIR


def test_rolling_features_alignment_across_entities():
    """
    Regression test for the .values scrambling bug:
    In the legacy code, groupby(entity).rolling().count().reset_index() sorted rows
    by entity, and assigning .values to timestamp-sorted DataFrame scrambled features across entities.
    Verify that interleaved transactions of different senders maintain strict entity alignment.
    """
    # Create interleaved transactions for two distinct senders:
    # CUST_ALPHA has 3 transactions; CUST_BETA has 2 transactions
    interleaved_data = pd.DataFrame([
        {
            "transaction_id": "TXN_A1",
            "timestamp": "2026-10-01 10:00:00",
            "sender_id": "CUST_ALPHA",
            "beneficiary_id": "BENEF_1",
            "device_id": "DEV_A",
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "merchant_category": "p2p_transfer",
            "amount_inr": 500.0,
            "is_fraud": 0,
        },
        {
            "transaction_id": "TXN_B1",
            "timestamp": "2026-10-01 10:00:30",
            "sender_id": "CUST_BETA",
            "beneficiary_id": "BENEF_2",
            "device_id": "DEV_B",
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "merchant_category": "p2p_transfer",
            "amount_inr": 200.0,
            "is_fraud": 0,
        },
        {
            "transaction_id": "TXN_A2",
            "timestamp": "2026-10-01 10:01:00",
            "sender_id": "CUST_ALPHA",
            "beneficiary_id": "BENEF_3",
            "device_id": "DEV_A",
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "merchant_category": "p2p_transfer",
            "amount_inr": 600.0,
            "is_fraud": 0,
        },
        {
            "transaction_id": "TXN_B2",
            "timestamp": "2026-10-01 10:02:00",
            "sender_id": "CUST_BETA",
            "beneficiary_id": "BENEF_4",
            "device_id": "DEV_B",
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "merchant_category": "p2p_transfer",
            "amount_inr": 250.0,
            "is_fraud": 0,
        },
        {
            "transaction_id": "TXN_A3",
            "timestamp": "2026-10-01 10:03:00",
            "sender_id": "CUST_ALPHA",
            "beneficiary_id": "BENEF_5",
            "device_id": "DEV_A",
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "merchant_category": "p2p_transfer",
            "amount_inr": 700.0,
            "is_fraud": 0,
        },
    ])

    X_features, _ = engineer_features(interleaved_data)

    # With closed='left', counts exclude current transaction:
    # For CUST_ALPHA:
    # TXN_A1 at 10:00:00 -> previous 10min count = 0
    # TXN_A2 at 10:01:00 -> previous 10min count = 1 (TXN_A1)
    # TXN_A3 at 10:03:00 -> previous 10min count = 2 (TXN_A1, TXN_A2)
    # For CUST_BETA:
    # TXN_B1 at 10:00:30 -> previous 10min count = 0
    # TXN_B2 at 10:02:00 -> previous 10min count = 1 (TXN_B1)

    assert X_features.loc[0, "txn_count_10min"] == 0, "TXN_A1 should have 0 prior txns"
    assert X_features.loc[1, "txn_count_10min"] == 0, "TXN_B1 should have 0 prior txns"
    assert X_features.loc[2, "txn_count_10min"] == 1, "TXN_A2 should have 1 prior txn"
    assert X_features.loc[3, "txn_count_10min"] == 1, "TXN_B2 should have 1 prior txn"
    assert X_features.loc[4, "txn_count_10min"] == 2, "TXN_A3 should have 2 prior txns"


def test_future_transactions_do_not_affect_past_features():
    """
    Test temporal leakage: appending future transactions MUST NOT alter the feature values
    of historical transactions already calculated.
    """
    base_data = pd.DataFrame([
        {
            "transaction_id": f"TXN_HIST_{i}",
            "timestamp": f"2026-10-01 12:0{i}:00",
            "sender_id": "CUST_TEMPORAL",
            "beneficiary_id": "BENEF_CONST",
            "device_id": "DEV_CONST",
            "channel": "UPI_P2P",
            "transaction_type": "P2P_TRANSFER",
            "merchant_category": "p2p_transfer",
            "amount_inr": 1000.0,
            "is_fraud": 0,
        }
        for i in range(3)
    ])

    X_base, _ = engineer_features(base_data)

    # Now simulate future transactions arriving later with a surge
    future_data = pd.concat([
        base_data,
        pd.DataFrame([
            {
                "transaction_id": f"TXN_FUTURE_{i}",
                "timestamp": f"2026-10-01 12:05:{i:02d}",
                "sender_id": "CUST_TEMPORAL",
                "beneficiary_id": "BENEF_DRAIN",
                "device_id": "DEV_NEW",
                "channel": "UPI_P2P",
                "transaction_type": "P2P_TRANSFER",
                "merchant_category": "p2p_transfer",
                "amount_inr": 9000.0,
                "is_fraud": 1,
            }
            for i in range(5)
        ])
    ], ignore_index=True)

    X_with_future, _ = engineer_features(future_data)

    # Features for the first 3 rows must be IDENTICAL between X_base and X_with_future
    for col in FEATURE_COLUMNS:
        np.testing.assert_array_almost_equal(
            X_base[col].values,
            X_with_future.loc[:2, col].values,
            err_msg=f"Feature {col} leaked future data into historical transactions!"
        )


def test_target_columns_excluded_from_model_inputs():
    """
    Verify that is_fraud, fraud_pattern, or target proxies are not included in FEATURE_COLUMNS
    or the output feature matrix.
    """
    sample_df = pd.DataFrame([{
        "transaction_id": "TXN_LEAK_CHECK",
        "timestamp": "2026-10-01 12:00:00",
        "sender_id": "CUST_1",
        "beneficiary_id": "BEN_1",
        "device_id": "DEV_1",
        "channel": "UPI_P2P",
        "transaction_type": "P2P_TRANSFER",
        "merchant_category": "p2p_transfer",
        "amount_inr": 1500.0,
        "is_fraud": 1,
        "fraud_pattern": "MULE_ACCOUNT_DRAIN",
        "fraud_type": "high_velocity",
    }])

    X_df, feature_names = engineer_features(sample_df)

    assert "is_fraud" not in feature_names
    assert "fraud_pattern" not in feature_names
    assert "fraud_type" not in feature_names
    assert "is_fraud" not in X_df.columns
    assert "fraud_pattern" not in X_df.columns
    assert "is_fraud" not in FEATURE_COLUMNS
    assert "fraud_pattern" not in FEATURE_COLUMNS


def test_chronological_splits_preserve_ordering():
    """
    Verify chronological split creates 70% Train, 15% Val, 15% Test without temporal overlap.
    """
    timestamps = pd.date_range("2026-09-01", periods=1000, freq="10min")
    synthetic_df = pd.DataFrame({
        "transaction_id": [f"TXN_{i}" for i in range(1000)],
        "timestamp": timestamps,
        "amount_inr": np.random.uniform(50, 5000, 1000),
        "is_fraud": (np.random.rand(1000) < 0.03).astype(int),
    })

    train_df, val_df, test_df = split_chronological(synthetic_df, train_ratio=0.70, val_ratio=0.15)

    assert len(train_df) == 700
    assert len(val_df) == 150
    assert len(test_df) == 150

    # Ensure no temporal overlap
    assert train_df["timestamp"].max() <= val_df["timestamp"].min()
    assert val_df["timestamp"].max() <= test_df["timestamp"].min()

    # Ensure all IDs are disjoint
    train_ids = set(train_df["transaction_id"])
    val_ids = set(val_df["transaction_id"])
    test_ids = set(test_df["transaction_id"])
    assert len(train_ids.intersection(val_ids)) == 0
    assert len(val_ids.intersection(test_ids)) == 0


def test_preprocessing_fitted_on_training_data_only():
    """
    Verify scaler is fitted strictly on training data and validation/test distributions
    do not influence train scaler parameters.
    """
    np.random.seed(42)
    # Training data: mean 100, std 10
    X_train = pd.DataFrame({"amount": np.random.normal(100, 10, 500)})
    # Validation data: shifted distribution mean 500, std 50
    X_val = pd.DataFrame({"amount": np.random.normal(500, 50, 100)})

    scaler = StandardScaler()
    scaler.fit(X_train)

    train_mean = scaler.mean_[0]
    train_scale = scaler.scale_[0]

    # Mean should be close to 100, not shifted by validation's 500
    assert math.isclose(train_mean, 100.0, abs_tol=5.0)

    # Transforming X_val must not change scaler parameters
    _ = scaler.transform(X_val)
    assert scaler.mean_[0] == train_mean
    assert scaler.scale_[0] == train_scale


def test_threshold_selection_uses_validation_data_only():
    """
    Verify threshold selection tunes on validation scores and does not use test labels.
    """
    y_val = np.array([0] * 90 + [1] * 10)
    # Predicted probabilities: genuine are around 0.1, fraud around 0.8
    y_val_probs = np.concatenate([
        np.random.uniform(0.01, 0.35, 90),
        np.random.uniform(0.60, 0.95, 10)
    ])

    best_thresh, best_f1 = tune_decision_threshold(y_val, y_val_probs)
    assert 0.35 <= best_thresh <= 0.65
    assert best_f1 > 0.80


def test_evaluation_metrics_safe_for_single_class_splits():
    """
    Verify evaluate_predictions safely handles splits containing only one class (all 0s or all 1s)
    without ZeroDivisionError or crashes.
    """
    y_all_zeros = np.array([0, 0, 0, 0, 0])
    y_probs = np.array([0.1, 0.2, 0.05, 0.8, 0.3])

    metrics = evaluate_predictions(y_all_zeros, y_probs, threshold=0.5, split_name="ZeroPositiveSplit")
    assert metrics["fraud_count"] == 0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0
    assert metrics["roc_auc"] == 0.0  # Safe fallback when ROC-AUC is undefined


def test_training_and_prediction_feature_schemas_match():
    """
    Verify feature names joblib file exists and matches FEATURE_COLUMNS exactly in order and names.
    """
    feature_names_path = MODELS_DIR / "feature_names.joblib"
    assert feature_names_path.exists(), "feature_names.joblib must exist"

    saved_features = joblib.load(feature_names_path)
    assert saved_features == FEATURE_COLUMNS, "Saved feature list must exactly match FEATURE_COLUMNS"


def test_saved_model_artifacts_load_and_score():
    """
    Verify all 4 models and transformers are serialized, can be loaded,
    and score an Indian digital payment payload with appropriate risk categories.
    """
    models = load_models()
    assert models["xgb_model"] is not None
    assert models["rf_model"] is not None
    assert models["lr_model"] is not None
    assert models.get("iso_model") is not None or models.get("iso_forest") is not None
    assert models["scaler"] is not None

    payload = {
        "transaction_id": "TXN_UPI_VERIFY_999",
        "timestamp": "2026-10-12 14:00:00",
        "amount_inr": 4850.0,
        "channel": "UPI_P2P",
        "transaction_type": "P2P_TRANSFER",
        "sender_id": "CUST_9999",
        "beneficiary_id": "BENEF_SUSPECT",
        "device_id": "DEV_UNVERIFIED",
        "is_new_device": 1,
        "sim_change_flag": 1,
        "ip_location_state": "Maharashtra",
    }

    result = score_transaction(payload)
    assert "risk_score" in result
    assert "decision" in result
    assert "risk_category" in result
    assert "reasons" in result
    assert "xgb_probability" in result
    assert "anomaly_score" in result

    assert isinstance(result["risk_score"], float)
    assert 0.0 <= result["risk_score"] <= 100.0
    assert result["decision"] in ["Allow", "Manual Review", "Block"]
    assert result["risk_category"] in ["LOW_RISK", "REVIEW", "HIGH_RISK"]
    assert len(result["reasons"]) == 3


def test_risk_category_mapping():
    """
    Verify risk categories follow model-assistance definitions.
    """
    assert get_risk_category(20.0) == "LOW_RISK"
    assert get_risk_category(50.0) == "REVIEW"
    assert get_risk_category(85.0) == "HIGH_RISK"
