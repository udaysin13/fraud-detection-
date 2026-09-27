"""
VaultGuard - Small Transaction Fraud Detection System
ml/generate_data.py

Generates synthetic transaction dataset (55,000 rows) with realistic small-value fraud patterns.
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Set random seed for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Data generation parameters
TOTAL_ROWS = 55000
FRAUD_TARGET_RATE = 0.020  # ~2.0%
NUM_FRAUD = int(TOTAL_ROWS * FRAUD_TARGET_RATE)  # ~1100 rows
NUM_LEGIT = TOTAL_ROWS - NUM_FRAUD  # ~53900 rows

# Segments and region mappings
SEGMENT_CONFIG = {
    "EU Payments": {
        "currencies": ["EUR", "GBP"],
        "countries": ["DE", "FR", "GB", "NL", "ES", "IT"],
    },
    "APAC Cards": {
        "currencies": ["SGD", "HKD", "JPY"],
        "countries": ["SG", "HK", "JP"],
    },
    "AU Cards": {"currencies": ["AUD"], "countries": ["AU", "NZ"]},
    "ME Cards": {"currencies": ["AED", "SAR"], "countries": ["AE", "SA"]},
    "AS Cards": {"currencies": ["USD", "CAD"], "countries": ["US", "CA"]},
}

SEGMENT_NAMES = list(SEGMENT_CONFIG.keys())
SEGMENT_PROBS = [0.30, 0.25, 0.15, 0.10, 0.20]

MERCHANT_CATEGORIES = [
    "digital_goods",
    "retail",
    "gaming",
    "food_delivery",
    "subscription",
    "travel",
    "rideshare",
    "crypto_exchange",
]

NORMAL_BINS = [
    "411111",
    "424242",
    "510000",
    "521111",
    "450000",
    "371234",
    "480000",
]
HIGH_RISK_BINS = ["499999", "599999", "379999", "549999"]

CHANNELS = ["mobile_app", "web", "pos", "api"]
CHANNEL_PROBS = [0.55, 0.30, 0.10, 0.05]


def random_ip():
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def generate_legitimate_transactions(count, start_time, end_time):
    """Generates baseline legitimate transactions."""
    rows = []
    total_seconds = int((end_time - start_time).total_seconds())

    for i in range(count):
        txn_id = f"TXN_LEGIT_{i+1:06d}"
        random_sec = random.randint(0, total_seconds)
        timestamp = start_time + timedelta(seconds=random_sec)

        card_num = random.randint(10000, 99999)
        card_id = f"CARD_{card_num}"
        customer_id = f"CUST_{random.randint(1000, 9999)}"
        merchant_id = f"MERCH_{random.randint(100, 999)}"
        merchant_category = random.choice(MERCHANT_CATEGORIES)

        # ~90% under $50, ~10% between $50 and $450
        if random.random() < 0.90:
            amount = round(float(np.random.exponential(scale=12.0)) + 0.50, 2)
            if amount > 49.99:
                amount = round(random.uniform(0.50, 49.99), 2)
        else:
            amount = round(random.uniform(50.00, 450.00), 2)

        segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
        seg_cfg = SEGMENT_CONFIG[segment]

        currency = random.choice(seg_cfg["currencies"])
        country = random.choice(seg_cfg["countries"])

        # 98% matching billing country
        if random.random() < 0.98:
            billing_country = country
        else:
            all_countries = ["US", "DE", "FR", "GB", "AU", "SG", "AE", "JP"]
            billing_country = random.choice(
                [c for c in all_countries if c != country]
            )

        device_id = f"DEV_{random.randint(10000, 99999)}"
        ip_address = random_ip()
        is_new_device = 1 if random.random() < 0.08 else 0
        bin_range = random.choice(NORMAL_BINS)
        channel = np.random.choice(CHANNELS, p=CHANNEL_PROBS)

        rows.append(
            {
                "transaction_id": txn_id,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "card_id": card_id,
                "customer_id": customer_id,
                "merchant_id": merchant_id,
                "merchant_category": merchant_category,
                "amount": amount,
                "currency": currency,
                "country": country,
                "billing_country": billing_country,
                "device_id": device_id,
                "ip_address": ip_address,
                "is_new_device": is_new_device,
                "bin_range": bin_range,
                "channel": channel,
                "segment": segment,
                "is_fraud": 0,
                "pattern": "Legitimate",
            }
        )

    return rows


def generate_fraud_transactions(count, start_time, end_time):
    """Generates synthetic fraudulent transactions categorized by 7 specific micro-fraud patterns."""
    rows = []

    # Target allocations for fraud patterns (sum = count)
    pattern_targets = {
        "Card Testing": int(count * 0.18),
        "Velocity Attack": int(count * 0.18),
        "Structuring": int(count * 0.18),
        "Geo Mismatch": int(count * 0.14),
        "New Device Surge": int(count * 0.12),
        "High-Risk BIN": int(count * 0.10),
        "Merchant Anomaly": count
        - (
            int(count * 0.18) * 3
            + int(count * 0.14)
            + int(count * 0.12)
            + int(count * 0.10)
        ),
    }

    total_seconds = int((end_time - start_time).total_seconds())
    txn_counter = 1

    # 1. Card Testing: Many $0.50-$5 charges in a few minutes
    target = pattern_targets["Card Testing"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(6, 12), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 300)
        )
        card_id = f"CARD_TEST_{random.randint(100, 999)}"
        customer_id = f"CUST_TEST_{random.randint(100, 999)}"
        merchant_id = f"MERCH_TEST_{random.randint(10, 99)}"

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(0, 180))
            amount = round(random.uniform(0.50, 4.99), 2)
            segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
            seg_cfg = SEGMENT_CONFIG[segment]

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "card_id": card_id,
                    "customer_id": customer_id,
                    "merchant_id": merchant_id,
                    "merchant_category": "digital_goods",
                    "amount": amount,
                    "currency": random.choice(seg_cfg["currencies"]),
                    "country": random.choice(seg_cfg["countries"]),
                    "billing_country": random.choice(seg_cfg["countries"]),
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "ip_address": random_ip(),
                    "is_new_device": 1 if random.random() < 0.6 else 0,
                    "bin_range": random.choice(NORMAL_BINS),
                    "channel": "web",
                    "segment": segment,
                    "is_fraud": 1,
                    "pattern": "Card Testing",
                }
            )
            txn_counter += 1
            generated += 1

    # 2. Velocity Attack: 10+ transactions in 10 minutes from one card
    target = pattern_targets["Velocity Attack"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(10, 15), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 600)
        )
        card_id = f"CARD_VEL_{random.randint(100, 999)}"
        customer_id = f"CUST_VEL_{random.randint(100, 999)}"

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(0, 540))
            amount = round(random.uniform(10.00, 45.00), 2)
            segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
            seg_cfg = SEGMENT_CONFIG[segment]

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "card_id": card_id,
                    "customer_id": customer_id,
                    "merchant_id": f"MERCH_{random.randint(100, 999)}",
                    "merchant_category": random.choice(MERCHANT_CATEGORIES),
                    "amount": amount,
                    "currency": random.choice(seg_cfg["currencies"]),
                    "country": random.choice(seg_cfg["countries"]),
                    "billing_country": random.choice(seg_cfg["countries"]),
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "ip_address": random_ip(),
                    "is_new_device": 1,
                    "bin_range": random.choice(NORMAL_BINS),
                    "channel": "mobile_app",
                    "segment": segment,
                    "is_fraud": 1,
                    "pattern": "Velocity Attack",
                }
            )
            txn_counter += 1
            generated += 1

    # 3. Structuring: Repeated amounts just below limit ($9.90, $49.50, $99.00)
    target = pattern_targets["Structuring"]
    generated = 0
    structuring_amounts = [9.90, 9.95, 19.90, 49.50, 49.90, 99.00]
    while generated < target:
        batch_size = min(random.randint(4, 8), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 3600)
        )
        card_id = f"CARD_STRUCT_{random.randint(100, 999)}"
        customer_id = f"CUST_STRUCT_{random.randint(100, 999)}"
        struct_amount = random.choice(structuring_amounts)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=b * random.randint(60, 300))
            segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
            seg_cfg = SEGMENT_CONFIG[segment]

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "card_id": card_id,
                    "customer_id": customer_id,
                    "merchant_id": f"MERCH_{random.randint(100, 999)}",
                    "merchant_category": "retail",
                    "amount": struct_amount,
                    "currency": random.choice(seg_cfg["currencies"]),
                    "country": random.choice(seg_cfg["countries"]),
                    "billing_country": random.choice(seg_cfg["countries"]),
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "ip_address": random_ip(),
                    "is_new_device": 0,
                    "bin_range": random.choice(NORMAL_BINS),
                    "channel": "web",
                    "segment": segment,
                    "is_fraud": 1,
                    "pattern": "Structuring",
                }
            )
            txn_counter += 1
            generated += 1

    # 4. Geo Mismatch: Billing country differs from transaction country
    target = pattern_targets["Geo Mismatch"]
    for g in range(target):
        txn_time = start_time + timedelta(seconds=random.randint(0, total_seconds))
        segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
        seg_cfg = SEGMENT_CONFIG[segment]
        country = random.choice(seg_cfg["countries"])

        mismatched_billing = {
            "US": "RU",
            "FR": "CN",
            "DE": "BR",
            "GB": "NG",
            "AU": "UA",
            "SG": "RO",
            "AE": "KP",
            "JP": "PK",
            "CA": "VN",
            "ES": "TR",
            "IT": "IR",
            "NL": "RU",
            "HK": "PH",
            "NZ": "IN",
            "SA": "BD",
        }
        billing_country = mismatched_billing.get(country, "RU")

        rows.append(
            {
                "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                "card_id": f"CARD_GEO_{random.randint(100, 999)}",
                "customer_id": f"CUST_GEO_{random.randint(100, 999)}",
                "merchant_id": f"MERCH_{random.randint(100, 999)}",
                "merchant_category": "crypto_exchange",
                "amount": round(random.uniform(15.00, 120.00), 2),
                "currency": random.choice(seg_cfg["currencies"]),
                "country": country,
                "billing_country": billing_country,
                "device_id": f"DEV_{random.randint(10000, 99999)}",
                "ip_address": random_ip(),
                "is_new_device": 1,
                "bin_range": random.choice(NORMAL_BINS),
                "channel": "api",
                "segment": segment,
                "is_fraud": 1,
                "pattern": "Geo Mismatch",
            }
        )
        txn_counter += 1

    # 5. New Device Surge: Many new devices on one account
    target = pattern_targets["New Device Surge"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(5, 8), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 1800)
        )
        customer_id = f"CUST_SURGE_{random.randint(100, 999)}"

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=b * random.randint(30, 180))
            segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
            seg_cfg = SEGMENT_CONFIG[segment]

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "card_id": f"CARD_{random.randint(10000, 99999)}",
                    "customer_id": customer_id,
                    "merchant_id": f"MERCH_{random.randint(100, 999)}",
                    "merchant_category": "gaming",
                    "amount": round(random.uniform(5.00, 35.00), 2),
                    "currency": random.choice(seg_cfg["currencies"]),
                    "country": random.choice(seg_cfg["countries"]),
                    "billing_country": random.choice(seg_cfg["countries"]),
                    "device_id": f"DEV_NEW_{random.randint(10000, 99999)}",
                    "ip_address": random_ip(),
                    "is_new_device": 1,
                    "bin_range": random.choice(NORMAL_BINS),
                    "channel": "mobile_app",
                    "segment": segment,
                    "is_fraud": 1,
                    "pattern": "New Device Surge",
                }
            )
            txn_counter += 1
            generated += 1

    # 6. High-Risk BIN Range: Transactions originating from suspicious BINs
    target = pattern_targets["High-Risk BIN"]
    for h in range(target):
        txn_time = start_time + timedelta(seconds=random.randint(0, total_seconds))
        segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
        seg_cfg = SEGMENT_CONFIG[segment]

        rows.append(
            {
                "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                "card_id": f"CARD_HR_{random.randint(100, 999)}",
                "customer_id": f"CUST_HR_{random.randint(100, 999)}",
                "merchant_id": f"MERCH_{random.randint(100, 999)}",
                "merchant_category": random.choice(MERCHANT_CATEGORIES),
                "amount": round(random.uniform(2.00, 48.00), 2),
                "currency": random.choice(seg_cfg["currencies"]),
                "country": random.choice(seg_cfg["countries"]),
                "billing_country": random.choice(seg_cfg["countries"]),
                "device_id": f"DEV_{random.randint(10000, 99999)}",
                "ip_address": random_ip(),
                "is_new_device": 1 if random.random() < 0.5 else 0,
                "bin_range": random.choice(HIGH_RISK_BINS),
                "channel": "web",
                "segment": segment,
                "is_fraud": 1,
                "pattern": "High-Risk BIN",
            }
        )
        txn_counter += 1

    # 7. Merchant Anomaly: Sudden volume spike at one merchant
    target = pattern_targets["Merchant Anomaly"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(15, 25), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 3600)
        )
        merchant_id = f"MERCH_SPIKE_{random.randint(10, 99)}"

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(0, 1800))
            segment = np.random.choice(SEGMENT_NAMES, p=SEGMENT_PROBS)
            seg_cfg = SEGMENT_CONFIG[segment]

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "card_id": f"CARD_{random.randint(10000, 99999)}",
                    "customer_id": f"CUST_{random.randint(1000, 9999)}",
                    "merchant_id": merchant_id,
                    "merchant_category": "digital_goods",
                    "amount": round(random.uniform(1.00, 15.00), 2),
                    "currency": random.choice(seg_cfg["currencies"]),
                    "country": random.choice(seg_cfg["countries"]),
                    "billing_country": random.choice(seg_cfg["countries"]),
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "ip_address": random_ip(),
                    "is_new_device": 1 if random.random() < 0.4 else 0,
                    "bin_range": random.choice(NORMAL_BINS),
                    "channel": "api",
                    "segment": segment,
                    "is_fraud": 1,
                    "pattern": "Merchant Anomaly",
                }
            )
            txn_counter += 1
            generated += 1

    return rows


def main():
    print("=" * 60)
    print(" VaultGuard - Generating Synthetic Small Transaction Dataset ")
    print("=" * 60)

    # Time frame: Last 30 days
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)

    # Generate datasets
    print(f"Generating {NUM_LEGIT:,} legitimate transactions...")
    legit_rows = generate_legitimate_transactions(NUM_LEGIT, start_time, end_time)

    print(f"Generating {NUM_FRAUD:,} fraudulent transactions across 7 patterns...")
    fraud_rows = generate_fraud_transactions(NUM_FRAUD, start_time, end_time)

    # Combine and sort by timestamp
    all_rows = legit_rows + fraud_rows
    df = pd.DataFrame(all_rows)

    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp_dt").reset_index(drop=True)

    # Separate pattern column for analysis, drop temporary datetime
    patterns = df["pattern"]
    df = df.drop(columns=["pattern", "timestamp_dt"])

    # Ensure output directory exists
    output_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "transactions.csv"

    # Save to CSV
    df.to_csv(output_csv, index=False)
    print(f"\n[SUCCESS] Saved {len(df):,} transactions to: {output_csv}\n")

    # Generate Summary Statistics
    df["pattern"] = patterns
    under_50_pct = (df["amount"] < 50.0).mean() * 100
    total_rows = len(df)
    total_fraud = int(df["is_fraud"].sum())
    overall_fraud_rate = (total_fraud / total_rows) * 100

    print("-" * 60)
    print(" SUMMARY STATISTICS")
    print("-" * 60)
    print(f"Total Rows Generated : {total_rows:,}")
    print(f"Transactions < $50   : {under_50_pct:.2f}%")
    print(f"Total Fraud Count    : {total_fraud:,}")
    print(f"Overall Fraud Rate   : {overall_fraud_rate:.2f}%\n")

    print("-" * 60)
    print(" FRAUD BREAKDOWN BY PATTERN")
    print("-" * 60)
    pattern_summary = (
        df[df["is_fraud"] == 1]
        .groupby("pattern")
        .agg(
            Fraud_Count=("is_fraud", "count"),
            Avg_Amount=("amount", "mean"),
            Min_Amount=("amount", "min"),
            Max_Amount=("amount", "max"),
        )
        .reset_index()
    )
    pattern_summary["Pct_of_Total_Fraud"] = (
        pattern_summary["Fraud_Count"] / total_fraud * 100
    )

    for _, row in pattern_summary.iterrows():
        print(
            f"- {row['pattern']:<20}: {row['Fraud_Count']:>4} txns ({row['Pct_of_Total_Fraud']:>5.2f}% of fraud) | "
            f"Avg: ${row['Avg_Amount']:>6.2f} (Range: ${row['Min_Amount']:>5.2f} - ${row['Max_Amount']:>6.2f})"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()
