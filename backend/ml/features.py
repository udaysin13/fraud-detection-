"""
VaultGuard - Indian Digital Payment Fraud Detection System
ml/features.py

Feature engineering module for Indian digital payment transactions (UPI, QR, IMPS, Wallets).
Extracts point-in-time velocity, past-only behavioral metrics, device/SIM change indicators,
new-beneficiary flags, structuring thresholds, and merchant spike ratios.

Leakage-Free Guarantee:
1. All rolling counts use `closed='left'`, strictly excluding the current transaction.
2. Grouped rolling results are aligned via unique point-in-time index keys (no array slicing).
3. Historical statistics use only prior transactions (expanding past-only windows).
4. No future records or target labels (is_fraud, fraud_pattern) are used in features.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

HIGH_RISK_BINS = {"499999", "599999", "379999", "549999"}

CATEGORICAL_COLS = ["channel", "transaction_type", "merchant_category"]

FEATURE_COLUMNS = [
    # Amounts & Flags
    "amount",
    "is_small_amount",
    "is_just_below_threshold",
    "amount_to_avg_ratio",
    # Temporal
    "hour_of_day",
    "day_of_week",
    "is_night",
    # Device & Security
    "is_new_device",
    "sim_change_flag",
    "high_risk_device_action",
    "time_since_last_txn",
    # Sender Velocity (Point-in-Time Rolling Prior Counts)
    "txn_count_1min",
    "txn_count_10min",
    "txn_count_1hour",
    "txn_count_24h",
    # Beneficiary & Merchant Dynamics
    "is_new_beneficiary",
    "merchant_spike_ratio",
    # Legacy compatibility indicators
    "geo_mismatch",
    "high_risk_bin",
    # Channel One-Hot Encodings
    "channel_UPI_P2M_QR",
    "channel_UPI_P2P",
    "channel_WALLET",
    "channel_IMPS",
    "channel_RUPAY_CARD",
    # Transaction Type One-Hot Encodings
    "txn_type_QR_PAYMENT",
    "txn_type_P2P_TRANSFER",
    "txn_type_MERCHANT_PAYMENT",
    "txn_type_COLLECT_REQUEST",
    # Merchant Category One-Hot Encodings
    "merchant_cat_food_dining",
    "merchant_cat_kirana_grocery",
    "merchant_cat_digital_services",
    "merchant_cat_transport_travel",
    "merchant_cat_retail_fashion",
    "merchant_cat_pharmacy_health",
    "merchant_cat_electronics",
    "merchant_cat_gaming_entertainment",
    "merchant_cat_p2p_transfer",
]


def check_just_below_threshold(amount: float) -> int:
    """
    Checks if transaction amount is just below common regulatory or surveillance thresholds:
    - INR 1,000 (e.g. INR 990 - 999)
    - INR 2,000 (e.g. INR 1,990 - 1,999)
    - INR 5,000 (e.g. INR 4,950 - 4,999)
    - INR 10,000 (e.g. INR 9,900 - 9,999)
    - Legacy thresholds: $10, $50, $100
    """
    thresholds = [1000.0, 2000.0, 5000.0, 10000.0, 10.0, 50.0, 100.0]
    for t in thresholds:
        # Check within 2% or 1 unit below the threshold
        lower_bound = min(t - 1.0, t - (t * 0.02))
        if lower_bound <= amount < t:
            return 1
    return 0


def engineer_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Engineers domain-specific point-in-time features from a transaction DataFrame.
    Guarantees strict temporal alignment, zero future leakage, and entity consistency.

    Returns:
        X_df: DataFrame containing engineered feature columns
        FEATURE_COLUMNS: List of feature column names
    """
    data = df.copy()

    # Track original row order to guarantee output index identity
    data["_orig_idx"] = np.arange(len(data))

    # Parse and sort chronologically by timestamp and transaction_id for deterministic ordering
    data["timestamp_dt"] = pd.to_datetime(data["timestamp"], errors="coerce")
    if data["timestamp_dt"].isna().any():
        data["timestamp_dt"] = data["timestamp_dt"].fillna(pd.Timestamp.now())

    if "transaction_id" in data.columns:
        data = data.sort_values(by=["timestamp_dt", "transaction_id"]).reset_index(drop=True)
    else:
        data = data.sort_values(by="timestamp_dt").reset_index(drop=True)

    # 1. Normalize field aliases (support both Indian UPI and legacy schema)
    if "amount_inr" in data.columns:
        amount_series = data["amount_inr"].astype(float)
    else:
        amount_series = data["amount"].astype(float)
    data["amount"] = amount_series

    sender_col = "sender_id" if "sender_id" in data.columns else ("customer_id" if "customer_id" in data.columns else "card_id")
    bene_col = "beneficiary_id" if "beneficiary_id" in data.columns else "merchant_id"

    # 2. Amount Flags & Structuring Checks
    data["is_small_amount"] = (data["amount"] < 100.0).astype(int)
    data["is_just_below_threshold"] = data["amount"].apply(check_just_below_threshold)

    # 3. Temporal Features
    data["hour_of_day"] = data["timestamp_dt"].dt.hour
    data["day_of_week"] = data["timestamp_dt"].dt.dayofweek
    data["is_night"] = data["hour_of_day"].isin([23, 0, 1, 2, 3, 4, 5]).astype(int)

    # 4. Device & Security Action Indicators
    if "is_new_device" in data.columns:
        data["is_new_device"] = data["is_new_device"].fillna(0).astype(int)
    else:
        data["is_new_device"] = 0

    if "sim_change_flag" in data.columns:
        data["sim_change_flag"] = data["sim_change_flag"].fillna(0).astype(int)
    else:
        data["sim_change_flag"] = 0

    data["high_risk_device_action"] = (
        (data["is_new_device"] == 1) & (data["sim_change_flag"] == 1)
    ).astype(int)

    # Legacy compatibility indicators
    if "country" in data.columns and "billing_country" in data.columns:
        data["geo_mismatch"] = (data["country"] != data["billing_country"]).astype(int)
    else:
        data["geo_mismatch"] = 0

    if "bin_range" in data.columns:
        data["high_risk_bin"] = (
            data["bin_range"].astype(str).isin(HIGH_RISK_BINS).astype(int)
        )
    else:
        data["high_risk_bin"] = 0

    # 5. Time Since Last Transaction per Sender
    data["prev_txn_time"] = data.groupby(sender_col)["timestamp_dt"].shift(1)
    data["time_since_last_txn"] = (
        (data["timestamp_dt"] - data["prev_txn_time"])
        .dt.total_seconds()
        .fillna(86400.0)
        .clip(lower=0.0, upper=86400.0)
    )
    data = data.drop(columns=["prev_txn_time"])

    # 6. Point-in-Time Rolling Velocity Counts per Sender
    if len(data) <= 1:
        data["txn_count_1min"] = 0
        data["txn_count_10min"] = 0
        data["txn_count_1hour"] = 0
        data["txn_count_24h"] = 0
    else:
        # To prevent Cartesian explosion on identical timestamps, add microsecond offset per sender
        data["_time_unique"] = data["timestamp_dt"] + pd.to_timedelta(
            data.groupby([sender_col, "timestamp_dt"]).cumcount(), unit="us"
        )
        if data["_time_unique"].isna().any():
            data["_time_unique"] = data["_time_unique"].fillna(pd.Timestamp.now())

        temp_s = data.set_index("_time_unique")
        velocity_windows = [
            ("1min", "txn_count_1min"),
            ("10min", "txn_count_10min"),
            ("1h", "txn_count_1hour"),
            ("24h", "txn_count_24h"),
        ]

        for window, col_name in velocity_windows:
            # closed='left' strictly excludes current transaction (prior transactions only)
            roll_s = (
                temp_s.groupby(sender_col)["amount"]
                .rolling(window, closed="left")
                .count()
                .rename(col_name)
            )
            data = data.merge(roll_s, on=[sender_col, "_time_unique"], how="left")
            data[col_name] = data[col_name].fillna(0).astype(int)

    # 7. Past-Only Expanding Amount Average & Ratio (Zero Future Leakage)
    # Uses only transactions preceding the current row for this sender
    cum_sum_prior = data.groupby(sender_col)["amount"].cumsum() - data["amount"]
    cum_cnt_prior = data.groupby(sender_col).cumcount()
    data["_prior_avg"] = np.where(
        cum_cnt_prior > 0,
        cum_sum_prior / cum_cnt_prior,
        data["amount"],
    )
    data["amount_to_avg_ratio"] = (
        data["amount"] / (data["_prior_avg"] + 1.0)
    ).clip(lower=0.0, upper=50.0)

    # 8. New Beneficiary Indicator (Point-in-Time)
    if bene_col in data.columns:
        # First time this sender transfers to this beneficiary = 1, subsequent = 0
        data["is_new_beneficiary"] = (
            data.groupby([sender_col, bene_col]).cumcount() == 0
        ).astype(int)
    else:
        data["is_new_beneficiary"] = 1

    # 9. Merchant Velocity Spike Ratio
    if "merchant_id" in data.columns and (data["merchant_id"] != "NOT_APPLICABLE").any():
        merch_mask = (data["merchant_id"] != "NOT_APPLICABLE") & (data["merchant_id"].notna())
        merch_subset = data[merch_mask].copy()

        if len(merch_subset) <= 1:
            data["merchant_spike_ratio"] = 1.0
        else:
            merch_subset["_time_merch"] = merch_subset["timestamp_dt"] + pd.to_timedelta(
                merch_subset.groupby(["merchant_id", "timestamp_dt"]).cumcount(), unit="us"
            )
            if merch_subset["_time_merch"].isna().any():
                merch_subset["_time_merch"] = merch_subset["_time_merch"].fillna(pd.Timestamp.now())
            temp_m = merch_subset.set_index("_time_merch")

            m_1h = (
                temp_m.groupby("merchant_id")["amount"]
                .rolling("1h", closed="left")
                .count()
                .rename("_m_cnt_1h")
            )
            m_24h = (
                temp_m.groupby("merchant_id")["amount"]
                .rolling("24h", closed="left")
                .count()
                .rename("_m_cnt_24h")
            )

            merch_subset = merch_subset.merge(m_1h, on=["merchant_id", "_time_merch"], how="left")
            merch_subset = merch_subset.merge(m_24h, on=["merchant_id", "_time_merch"], how="left")

            merch_subset["merchant_spike_ratio"] = (
                merch_subset["_m_cnt_1h"].fillna(0)
                / ((merch_subset["_m_cnt_24h"].fillna(0) / 24.0) + 1.0)
            ).clip(lower=0.0, upper=50.0)

            # Merge spike ratio back
            data = data.merge(
                merch_subset[["_orig_idx", "merchant_spike_ratio"]],
                on="_orig_idx",
                how="left",
            )
            data["merchant_spike_ratio"] = data["merchant_spike_ratio"].fillna(1.0)
    else:
        data["merchant_spike_ratio"] = 1.0

    # 10. Categorical One-Hot Encodings
    channel_col = (
        data["channel"]
        if "channel" in data.columns
        else pd.Series(["UPI_P2P"] * len(data), index=data.index)
    )
    data["channel_UPI_P2M_QR"] = (channel_col == "UPI_P2M_QR").astype(int)
    data["channel_UPI_P2P"] = (channel_col == "UPI_P2P").astype(int)
    data["channel_WALLET"] = (channel_col == "WALLET").astype(int)
    data["channel_IMPS"] = (channel_col == "IMPS").astype(int)
    data["channel_RUPAY_CARD"] = (channel_col == "RUPAY_CARD").astype(int)

    ttype_col = (
        data["transaction_type"]
        if "transaction_type" in data.columns
        else pd.Series(["P2P_TRANSFER"] * len(data), index=data.index)
    )
    data["txn_type_QR_PAYMENT"] = (ttype_col == "QR_PAYMENT").astype(int)
    data["txn_type_P2P_TRANSFER"] = (ttype_col == "P2P_TRANSFER").astype(int)
    data["txn_type_MERCHANT_PAYMENT"] = (ttype_col == "MERCHANT_PAYMENT").astype(int)
    data["txn_type_COLLECT_REQUEST"] = (ttype_col == "COLLECT_REQUEST").astype(int)

    mcat_col = (
        data["merchant_category"]
        if "merchant_category" in data.columns
        else pd.Series(["p2p_transfer"] * len(data), index=data.index)
    )
    data["merchant_cat_food_dining"] = (mcat_col == "food_dining").astype(int)
    data["merchant_cat_kirana_grocery"] = (mcat_col == "kirana_grocery").astype(int)
    data["merchant_cat_digital_services"] = (mcat_col == "digital_services").astype(int)
    data["merchant_cat_transport_travel"] = (mcat_col == "transport_travel").astype(int)
    data["merchant_cat_retail_fashion"] = (mcat_col == "retail_fashion").astype(int)
    data["merchant_cat_pharmacy_health"] = (mcat_col == "pharmacy_health").astype(int)
    data["merchant_cat_electronics"] = (mcat_col == "electronics").astype(int)
    data["merchant_cat_gaming_entertainment"] = (mcat_col == "gaming_entertainment").astype(int)
    data["merchant_cat_p2p_transfer"] = (mcat_col == "p2p_transfer").astype(int)

    # 11. Restore original row order
    data = data.sort_values(by="_orig_idx").reset_index(drop=True)

    # 12. Ensure all required feature columns exist and are numeric
    for col in FEATURE_COLUMNS:
        if col not in data.columns:
            data[col] = 0.0
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)

    X_df = data[FEATURE_COLUMNS].copy()
    return X_df, FEATURE_COLUMNS


def extract_single_txn_features(
    txn: Dict, history_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Extracts features for a single real-time transaction dict using historical context
    if available, or realistic standalone defaults.
    """
    txn_copy = txn.copy()
    if "timestamp" not in txn_copy or not txn_copy["timestamp"]:
        txn_copy["timestamp"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    # Map amount
    if "amount" not in txn_copy and "amount_inr" in txn_copy:
        txn_copy["amount"] = txn_copy["amount_inr"]
    elif "amount" in txn_copy and "amount_inr" not in txn_copy:
        txn_copy["amount_inr"] = txn_copy["amount"]

    single_df = pd.DataFrame([txn_copy])

    if history_df is not None and not history_df.empty:
        # Prepend historical context for velocity calculations
        combined_df = pd.concat([history_df, single_df], ignore_index=True)
        combined_features, _ = engineer_features(combined_df)
        return combined_features.tail(1).reset_index(drop=True)
    else:
        # Standalone extraction
        single_features, _ = engineer_features(single_df)
        return single_features
