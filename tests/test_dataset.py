"""
VaultGuard - Unit Tests for Indian UPI Dataset & Data Schema (Phase 2)
"""

from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.generate_data import (
    generate_dataset,
    CHANNELS,
    TOTAL_ROWS,
    SEED,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "transactions.csv"

REQUIRED_COLUMNS = [
    "transaction_id",
    "timestamp",
    "amount_inr",
    "channel",
    "transaction_type",
    "sender_id",
    "beneficiary_id",
    "sender_vpa",
    "beneficiary_vpa",
    "merchant_id",
    "merchant_category",
    "device_id",
    "is_new_device",
    "sim_change_flag",
    "ip_location_state",
    "transaction_status",
    "is_fraud",
    "fraud_pattern",
]

BACKWARD_COMPAT_COLUMNS = [
    "amount",
    "customer_id",
    "card_id",
    "currency",
    "country",
    "billing_country",
    "bin_range",
    "segment",
    "pattern",
]


@pytest.fixture(scope="module")
def dataset_df():
    """Loads transactions.csv fixture for fast testing."""
    assert CSV_PATH.exists(), f"Dataset file not found at {CSV_PATH}"
    df = pd.read_csv(CSV_PATH)
    return df


def test_dataset_file_exists_and_row_count(dataset_df):
    """Verifies dataset exists and contains exactly the expected row count."""
    assert len(dataset_df) == TOTAL_ROWS
    assert len(dataset_df) == 55000


def test_dataset_required_columns_and_no_missing_values(dataset_df):
    """Verifies all primary Indian UPI schema fields exist with no null values."""
    for col in REQUIRED_COLUMNS:
        assert col in dataset_df.columns, f"Missing required column: {col}"
    
    null_counts = dataset_df[REQUIRED_COLUMNS].isnull().sum()
    assert null_counts.sum() == 0, f"Found null values in dataset: {null_counts.to_dict()}"


def test_dataset_backward_compatibility_columns(dataset_df):
    """Verifies legacy columns exist to prevent breakage in un-migrated services."""
    for col in BACKWARD_COMPAT_COLUMNS:
        assert col in dataset_df.columns, f"Missing compatibility column: {col}"
    assert (dataset_df["amount"] == dataset_df["amount_inr"]).all()
    assert (dataset_df["currency"] == "INR").all()


def test_dataset_unique_transaction_ids(dataset_df):
    """Verifies every transaction ID is unique."""
    assert dataset_df["transaction_id"].nunique() == len(dataset_df)


def test_dataset_chronological_ordering(dataset_df):
    """Verifies transactions are sorted in non-decreasing chronological order."""
    timestamps = pd.to_datetime(dataset_df["timestamp"])
    assert timestamps.is_monotonic_increasing, "Dataset is not sorted chronologically!"


def test_dataset_valid_timestamp_format(dataset_df):
    """Verifies timestamps match the standard YYYY-MM-DD HH:MM:SS format."""
    # Test sample of 100 random rows for speed
    sample = dataset_df["timestamp"].sample(100, random_state=42)
    for ts in sample:
        parsed = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        assert parsed is not None


def test_dataset_valid_channels(dataset_df):
    """Verifies all channels belong to the approved Indian payment channel set."""
    channels_in_df = set(dataset_df["channel"].unique())
    expected_channels = set(CHANNELS)
    assert channels_in_df.issubset(expected_channels)


def test_dataset_non_negative_inr_amounts(dataset_df):
    """Verifies all INR amounts are positive numbers."""
    assert (dataset_df["amount_inr"] > 0).all()
    assert dataset_df["amount_inr"].min() >= 1.0


def test_dataset_binary_fraud_labels(dataset_df):
    """Verifies fraud labels are strictly binary (0 or 1)."""
    labels = set(dataset_df["is_fraud"].unique())
    assert labels == {0, 1}


def test_dataset_plausible_distributions(dataset_df):
    """Verifies realistic payment channel, micro-transaction and fraud distributions."""
    fraud_rate = dataset_df["is_fraud"].mean() * 100
    assert 1.0 <= fraud_rate <= 5.0, f"Fraud rate {fraud_rate}% outside realistic window (1%-5%)"

    # UPI channels should account for majority (> 65%) of Indian digital payments
    upi_pct = dataset_df["channel"].isin(["UPI_P2M_QR", "UPI_P2P"]).mean() * 100
    assert upi_pct >= 65.0, f"UPI volume {upi_pct}% is lower than expected"

    # Micro-transactions (< INR 1,000) should represent high majority (> 60%)
    micro_pct = (dataset_df["amount_inr"] < 1000.0).mean() * 100
    assert micro_pct >= 60.0

    # Verify presence of multiple realistic fraud patterns
    fraud_df = dataset_df[dataset_df["is_fraud"] == 1]
    patterns = set(fraud_df["fraud_pattern"].unique())
    assert len(patterns) >= 5, f"Expected at least 5 distinct fraud patterns, got {len(patterns)}"
    assert "Rapid Micro-Transfers" in patterns
    assert "SIM Change Takeover" in patterns
    assert "QR Merchant Spike" in patterns


def test_dataset_deterministic_reproducibility():
    """Verifies that the generator generates byte-for-byte identical output with SEED=42."""
    df1 = generate_dataset()
    df2 = generate_dataset()
    pd.testing.assert_frame_equal(df1, df2)
