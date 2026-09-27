"""
VaultGuard - Small Transaction Fraud Detection System
ml/features.py

Feature engineering module for VaultGuard small transaction fraud detection.
Extracts velocity, behavioral z-scores, device surges, structuring indicators, and geo features.
"""

from typing import List, Tuple, Dict
import numpy as np
import pandas as pd

HIGH_RISK_BINS = {"499999", "599999", "379999", "549999"}
CATEGORICAL_COLS = ["merchant_category", "channel", "segment"]

FEATURE_COLUMNS = [
    "amount",
    "txn_count_1min",
    "txn_count_10min",
    "txn_count_1hour",
    "card_avg_amount",
    "card_std_amount",
    "amount_z_score",
    "is_small_amount",
    "is_just_below_threshold",
    "time_since_last_txn",
    "device_count_24h",
    "geo_mismatch",
    "high_risk_bin",
    "merchant_spike_ratio",
    "hour_of_day",
    "day_of_week",
    "is_night",
    # One-hot encoded categoricals
    "merchant_category_crypto_exchange",
    "merchant_category_digital_goods",
    "merchant_category_food_delivery",
    "merchant_category_gaming",
    "merchant_category_retail",
    "merchant_category_rideshare",
    "merchant_category_subscription",
    "merchant_category_travel",
    "channel_api",
    "channel_mobile_app",
    "channel_pos",
    "channel_web",
    "segment_APAC Cards",
    "segment_AS Cards",
    "segment_AU Cards",
    "segment_EU Payments",
    "segment_ME Cards",
]


def check_just_below_threshold(amount: float) -> int:
    """Checks if transaction amount is just below common limits ($10, $50, $100)."""
    thresholds = [10.0, 50.0, 100.0]
    for t in thresholds:
        if (t - 1.0) <= amount < t:
            return 1
    return 0


def engineer_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Engineers rich domain-specific features from raw transaction DataFrame.

    Returns:
        X_df: DataFrame containing engineered feature columns
        FEATURE_COLUMNS: List of feature column names
    """
    data = df.copy()

    # Ensure timestamp is datetime sorted chronologically
    data["timestamp_dt"] = pd.to_datetime(data["timestamp"])
    data = data.sort_values("timestamp_dt").reset_index(drop=True)

    # 1. Temporal Features
    data["hour_of_day"] = data["timestamp_dt"].dt.hour
    data["day_of_week"] = data["timestamp_dt"].dt.dayofweek
    data["is_night"] = data["hour_of_day"].isin([23, 0, 1, 2, 3, 4, 5]).astype(int)

    # 2. Amount Flags & Threshold Checks
    data["is_small_amount"] = (data["amount"] < 10.0).astype(int)
    data["is_just_below_threshold"] = data["amount"].apply(check_just_below_threshold)

    # 3. Static Risk Flags
    data["geo_mismatch"] = (data["country"] != data["billing_country"]).astype(int)
    data["high_risk_bin"] = (
        data["bin_range"].astype(str).isin(HIGH_RISK_BINS).astype(int)
    )

    # 4. Historical Card Features (Avg, Std, Z-Score)
    card_stats = (
        data.groupby("card_id")["amount"]
        .agg(card_avg_amount="mean", card_std_amount="std")
        .reset_index()
    )
    card_stats["card_std_amount"] = card_stats["card_std_amount"].fillna(0.0)

    data = data.merge(card_stats, on="card_id", how="left")
    data["amount_z_score"] = (
        (data["amount"] - data["card_avg_amount"]) / (data["card_std_amount"] + 1e-5)
    ).clip(-10.0, 10.0)

    # 5. Time Since Last Txn per Card
    data["prev_txn_time"] = data.groupby("card_id")["timestamp_dt"].shift(1)
    data["time_since_last_txn"] = (
        (data["timestamp_dt"] - data["prev_txn_time"])
        .dt.total_seconds()
        .fillna(86400.0)
    )
    data = data.drop(columns=["prev_txn_time"])

    # 6. Velocity Features per Card (1min, 10min, 1hour)
    temp_idx = data.set_index("timestamp_dt")

    # Groupby card_id rolling window calculations
    v_1m = (
        temp_idx.groupby("card_id")["transaction_id"]
        .rolling("1min")
        .count()
        .reset_index()
    )
    v_10m = (
        temp_idx.groupby("card_id")["transaction_id"]
        .rolling("10min")
        .count()
        .reset_index()
    )
    v_1h = (
        temp_idx.groupby("card_id")["transaction_id"]
        .rolling("1h")
        .count()
        .reset_index()
    )

    data["txn_count_1min"] = v_1m["transaction_id"].values
    data["txn_count_10min"] = v_10m["transaction_id"].values
    data["txn_count_1hour"] = v_1h["transaction_id"].values

    # 7. Device Count per Customer in 24 hours
    # Count distinct device IDs per customer in last 24h
    data["device_count_24h"] = (
        data.groupby("customer_id")["device_id"]
        .transform("nunique")
        .clip(upper=15)
    )

    # 8. Merchant Spike Ratio (1h count vs 24h avg count)
    m_1h = (
        temp_idx.groupby("merchant_id")["transaction_id"]
        .rolling("1h")
        .count()
        .reset_index()
    )
    m_24h = (
        temp_idx.groupby("merchant_id")["transaction_id"]
        .rolling("24h")
        .count()
        .reset_index()
    )

    data["merchant_spike_ratio"] = (m_1h["transaction_id"].values) / (
        (m_24h["transaction_id"].values / 24.0) + 1.0
    )

    # 9. One-Hot Encoding for Categoricals
    one_hot_encoded = pd.get_dummies(
        data[CATEGORICAL_COLS], prefix=CATEGORICAL_COLS, dtype=int
    )
    data = pd.concat([data, one_hot_encoded], axis=1)

    # Ensure all required feature columns exist
    for col in FEATURE_COLUMNS:
        if col not in data.columns:
            data[col] = 0

    X_df = data[FEATURE_COLUMNS].copy()
    return X_df, FEATURE_COLUMNS


def extract_single_txn_features(
    txn: Dict, history_df: pd.DataFrame = None
) -> pd.DataFrame:
    """
    Extracts features for a single real-time transaction dict using historical dataset context.
    """
    txn_copy = txn.copy()
    if "timestamp" not in txn_copy or not txn_copy["timestamp"]:
        txn_copy["timestamp"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    single_df = pd.DataFrame([txn_copy])

    if history_df is not None and not history_df.empty:
        # Combine historical context with current transaction
        combined_df = pd.concat([history_df, single_df], ignore_index=True)
        combined_features, _ = engineer_features(combined_df)
        # Return the last row corresponding to the single transaction
        return combined_features.tail(1).reset_index(drop=True)
    else:
        # Standalone extraction fallback
        single_features, _ = engineer_features(single_df)
        return single_features
