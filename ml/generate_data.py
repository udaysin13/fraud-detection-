"""
VaultGuard - Indian Digital Payment Fraud Detection System
ml/generate_data.py

Generates a deterministic synthetic dataset (~55,000 transactions) modeling
Indian digital payment workflows (UPI P2P, UPI P2M QR, IMPS, RuPay, Wallets)
with realistic small-value fraud scenarios and legitimate transaction distributions.

Explicit Disclosure:
This dataset is strictly synthetic for academic and demonstration purposes.
It is NOT sourced from NPCI, RBI, commercial banks, or actual UPI networks.
"""

import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# Configure stdout for safe UTF-8 terminal output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Set fixed random seed for 100% deterministic reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Generation scale parameters
TOTAL_ROWS = 55000
FRAUD_TARGET_RATE = 0.022  # ~2.2% fraud prevalence
NUM_FRAUD = int(TOTAL_ROWS * FRAUD_TARGET_RATE)  # 1,210 rows
NUM_LEGIT = TOTAL_ROWS - NUM_FRAUD  # 53,790 rows

# Fixed 30-day time window for reproducible timestamps
FIXED_END_TIME = datetime(2026, 10, 12, 12, 0, 0)
FIXED_START_TIME = FIXED_END_TIME - timedelta(days=30)

# Payment channels and transaction types
CHANNELS = ["UPI_P2M_QR", "UPI_P2P", "WALLET", "IMPS", "RUPAY_CARD"]
CHANNEL_WEIGHTS = [0.45, 0.35, 0.10, 0.05, 0.05]

TRANSACTION_STATUSES = ["SUCCESS", "FAILED", "PENDING"]
STATUS_WEIGHTS = [0.975, 0.020, 0.005]

# Indian States and Union Territories for realistic geolocation
INDIAN_STATES = [
    "Maharashtra",
    "Karnataka",
    "Delhi",
    "Tamil Nadu",
    "Uttar Pradesh",
    "Gujarat",
    "Telangana",
    "West Bengal",
    "Rajasthan",
    "Kerala",
    "Haryana",
    "Madhya Pradesh",
    "Punjab",
    "Bihar",
    "Odisha",
    "Assam",
]
STATE_WEIGHTS = [
    0.16,
    0.14,
    0.12,
    0.10,
    0.08,
    0.07,
    0.07,
    0.06,
    0.04,
    0.04,
    0.03,
    0.03,
    0.02,
    0.02,
    0.01,
    0.01,
]

# Synthetic VPA bank handles
VPA_HANDLES = [
    "@okhdfcbank",
    "@okaxis",
    "@oksbi",
    "@okicici",
    "@paytm",
    "@ybl",
    "@ibl",
    "@upi",
    "@kotak",
    "@barodampay",
]

# Indian user name parts for synthetic VPA generation
FIRST_NAMES = [
    "aarav",
    "rohit",
    "priya",
    "ananya",
    "vikram",
    "rajesh",
    "sneha",
    "arjun",
    "pooja",
    "kavita",
    "amit",
    "sunil",
    "neha",
    "rahul",
    "deepak",
    "meera",
    "sanjay",
    "divya",
    "manish",
    "ritu",
    "aditya",
    "shreya",
    "karthik",
    "swati",
    "varun",
    "ankita",
    "tarun",
    "tanvi",
]

LAST_NAMES = [
    "sharma",
    "verma",
    "singh",
    "patel",
    "kumar",
    "gupta",
    "joshi",
    "mehta",
    "nair",
    "rao",
    "reddy",
    "iyer",
    "das",
    "chatterjee",
    "deshmukh",
    "kulkarni",
]

# Synthetic Indian Merchant Catalog
MERCHANT_CATALOG = [
    {
        "id": "MERCH_IND_101",
        "category": "food_dining",
        "vpa": "chai.point@icici",
        "name": "Chai & Snacks Corner",
        "avg_amount": 45.0,
    },
    {
        "id": "MERCH_IND_102",
        "category": "kirana_grocery",
        "vpa": "apna.kirana@paytm",
        "name": "Apna Super Kirana",
        "avg_amount": 180.0,
    },
    {
        "id": "MERCH_IND_103",
        "category": "food_dining",
        "vpa": "swiggy.orders@hdfcbank",
        "name": "Swiggy Online Food",
        "avg_amount": 320.0,
    },
    {
        "id": "MERCH_IND_104",
        "category": "food_dining",
        "vpa": "zomato.online@icici",
        "name": "Zomato Delivery",
        "avg_amount": 340.0,
    },
    {
        "id": "MERCH_IND_105",
        "category": "digital_services",
        "vpa": "recharge.jio@paytm",
        "name": "Jio Prepaid Recharge",
        "avg_amount": 299.0,
    },
    {
        "id": "MERCH_IND_106",
        "category": "transport_travel",
        "vpa": "ola.rides@okaxis",
        "name": "Ola Cab Mobility",
        "avg_amount": 160.0,
    },
    {
        "id": "MERCH_IND_107",
        "category": "transport_travel",
        "vpa": "uber.india@hdfcbank",
        "name": "Uber India Rides",
        "avg_amount": 190.0,
    },
    {
        "id": "MERCH_IND_108",
        "category": "retail_fashion",
        "vpa": "myntra.pay@icici",
        "name": "Myntra Fashion App",
        "avg_amount": 850.0,
    },
    {
        "id": "MERCH_IND_109",
        "category": "pharmacy_health",
        "vpa": "apollo.pharmacy@hdfcbank",
        "name": "Apollo Quick Pharmacy",
        "avg_amount": 240.0,
    },
    {
        "id": "MERCH_IND_110",
        "category": "digital_services",
        "vpa": "hotstar.sub@hdfcbank",
        "name": "Disney+ Hotstar Sub",
        "avg_amount": 149.0,
    },
    {
        "id": "MERCH_IND_111",
        "category": "gaming_entertainment",
        "vpa": "dream11.play@icici",
        "name": "Dream11 Contest",
        "avg_amount": 120.0,
    },
    {
        "id": "MERCH_IND_112",
        "category": "electronics",
        "vpa": "croma.retail@hdfcbank",
        "name": "Croma Electronics Store",
        "avg_amount": 2490.0,
    },
]

# Synthetic Bank IFSC routing prefixes
IFSC_PREFIXES = [
    "HDFC0001042",
    "SBIN0004910",
    "ICIC0000392",
    "UTIB0001290",
    "PYTM0123456",
    "KKBK0000192",
    "BARB0MUMBAI",
    "PUNB0291000",
]


def generate_synthetic_vpa(user_index: int) -> str:
    """Generates a deterministic, realistic synthetic Indian VPA."""
    fname = FIRST_NAMES[user_index % len(FIRST_NAMES)]
    lname = LAST_NAMES[(user_index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    handle = VPA_HANDLES[user_index % len(VPA_HANDLES)]
    tag = (user_index % 99) + 1
    return f"{fname}.{lname}{tag}{handle}"


def generate_simulated_ip() -> str:
    """Generates a synthetic IP address within typical Indian ISP subnets."""
    subnets = ["49.32", "103.21", "157.48", "122.161", "106.51", "27.56"]
    base = random.choice(subnets)
    return f"{base}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def map_channel_to_segment(channel: str) -> str:
    """Maps payment channel to a readable segment name."""
    segment_map = {
        "UPI_P2M_QR": "UPI P2M QR",
        "UPI_P2P": "UPI P2P",
        "WALLET": "Digital Wallet",
        "IMPS": "IMPS Transfer",
        "RUPAY_CARD": "RuPay Digital",
    }
    return segment_map.get(channel, "UPI Digital")


def generate_legitimate_transactions(
    count: int, start_time: datetime, end_time: datetime
) -> List[Dict]:
    """
    Generates baseline legitimate Indian digital transactions.

    Distribution features:
    - ~75% micro/small transfers (< ₹500)
    - ~18% medium transfers (₹500 - ₹2,500)
    - ~7% larger transfers (₹2,500 - ₹25,000)
    - Realistic overlap: ~6% new device, ~1.5% recent SIM change, ~12% night hours
    """
    rows = []
    total_seconds = int((end_time - start_time).total_seconds())

    # Pre-generate a pool of 3,500 sender profiles for recurring behavioural patterns
    user_pool = []
    for u in range(3500):
        sender_id = f"CUST_IND_{1000 + u}"
        sender_vpa = generate_synthetic_vpa(u)
        primary_device = f"DEV_IND_{10000 + u}"
        home_state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)
        user_pool.append(
            {
                "sender_id": sender_id,
                "sender_vpa": sender_vpa,
                "primary_device": primary_device,
                "home_state": home_state,
                "user_idx": u,
            }
        )

    for i in range(count):
        txn_id = f"TXN_LEGIT_{i+1:06d}"
        random_sec = random.randint(0, total_seconds)
        timestamp = start_time + timedelta(seconds=random_sec)

        user = random.choice(user_pool)
        channel = np.random.choice(CHANNELS, p=CHANNEL_WEIGHTS)
        state = (
            user["home_state"]
            if random.random() < 0.94
            else np.random.choice(INDIAN_STATES)
        )

        # Realistic Indian transaction amounts
        r_amt = random.random()
        if r_amt < 0.50:
            # Micro charges: chai, snacks, auto, kirana (₹10 - ₹150)
            amount = round(float(np.random.exponential(scale=35.0)) + 10.0, 2)
            if amount > 150.0:
                amount = round(random.uniform(10.0, 150.0), 2)
        elif r_amt < 0.75:
            # Small transfers: meals, pharmacy, small groceries (₹150 - ₹500)
            amount = round(random.uniform(150.0, 500.0), 2)
        elif r_amt < 0.93:
            # Medium transfers: supermarket, utilities, dinners (₹500 - ₹2,500)
            amount = round(random.uniform(500.0, 2500.0), 2)
        else:
            # Larger transfers: rent, electronics, travel (₹2,500 - ₹25,000)
            amount = round(random.uniform(2500.0, 25000.0), 2)

        # Channel specific mappings
        if channel in ["UPI_P2M_QR", "WALLET", "RUPAY_CARD"]:
            merch = random.choice(MERCHANT_CATALOG)
            merchant_id = merch["id"]
            merchant_category = merch["category"]
            beneficiary_id = merchant_id
            beneficiary_vpa = merch["vpa"]
            txn_type = "QR_PAYMENT" if channel == "UPI_P2M_QR" else "MERCHANT_PAYMENT"
        else:
            # UPI_P2P or IMPS
            dest_user = random.choice(user_pool)
            while dest_user["sender_id"] == user["sender_id"]:
                dest_user = random.choice(user_pool)
            merchant_id = "NOT_APPLICABLE"
            merchant_category = "p2p_transfer"
            beneficiary_id = f"BEN_IND_{dest_user['user_idx'] + 1000}"
            beneficiary_vpa = dest_user["sender_vpa"]
            txn_type = "P2P_TRANSFER"

        # Realistic noise: legitimate users occasionally switch devices or port SIMs
        is_new_device = 1 if random.random() < 0.06 else 0
        sim_change_flag = 1 if random.random() < 0.015 else 0
        device_id = (
            user["primary_device"]
            if is_new_device == 0
            else f"DEV_IND_{random.randint(50000, 99999)}"
        )

        txn_status = np.random.choice(TRANSACTION_STATUSES, p=STATUS_WEIGHTS)
        ifsc_code = IFSC_PREFIXES[user["user_idx"] % len(IFSC_PREFIXES)]
        segment = map_channel_to_segment(channel)

        rows.append(
            {
                # New Primary Indian UPI Schema
                "transaction_id": txn_id,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "amount_inr": amount,
                "channel": channel,
                "transaction_type": txn_type,
                "sender_id": user["sender_id"],
                "beneficiary_id": beneficiary_id,
                "sender_vpa": user["sender_vpa"],
                "beneficiary_vpa": beneficiary_vpa,
                "merchant_id": merchant_id,
                "merchant_category": merchant_category,
                "device_id": device_id,
                "is_new_device": is_new_device,
                "sim_change_flag": sim_change_flag,
                "ip_location_state": state,
                "transaction_status": txn_status,
                "is_fraud": 0,
                "fraud_pattern": "Legitimate",
                # Backward-compatibility alias columns
                "amount": amount,
                "customer_id": user["sender_id"],
                "card_id": user["sender_vpa"],
                "currency": "INR",
                "country": "IN",
                "billing_country": "IN",
                "bin_range": ifsc_code[:6],
                "segment": segment,
                "ip_address": generate_simulated_ip(),
                "pattern": "Legitimate",
            }
        )

    return rows


def generate_fraud_transactions(
    count: int, start_time: datetime, end_time: datetime
) -> List[Dict]:
    """
    Generates synthetic fraudulent Indian digital transactions categorized by
    6 independently documented small-transaction fraud scenarios:

    1. Rapid Micro-Transfers (UPI Testing Attack)
    2. Unusual New Beneficiary Burst
    3. SIM Change Takeover (SIM Swap + Account Hijack)
    4. QR Merchant Velocity Spike (Mule QR / Terminal Anomaly)
    5. Phishing Collect Request Spoofing
    6. Structuring Split Transfers (Sub-Threshold Smurfing)
    """
    rows = []

    # Partition targets across the 6 patterns (sum = count)
    pattern_targets = {
        "Rapid Micro-Transfers": int(count * 0.20),
        "New Beneficiary Burst": int(count * 0.18),
        "SIM Change Takeover": int(count * 0.18),
        "QR Merchant Spike": int(count * 0.16),
        "Phishing Collect Request": int(count * 0.14),
        "Structuring Split Transfer": count
        - (
            int(count * 0.20)
            + int(count * 0.18)
            + int(count * 0.18)
            + int(count * 0.16)
            + int(count * 0.14)
        ),
    }

    total_seconds = int((end_time - start_time).total_seconds())
    txn_counter = 1

    # ---------------------------------------------------------
    # 1. Rapid Micro-Transfers (UPI Testing Attack)
    # ---------------------------------------------------------
    target = pattern_targets["Rapid Micro-Transfers"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(6, 10), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 300)
        )
        sender_id = f"CUST_ATK_{random.randint(100, 999)}"
        sender_vpa = f"test.victim{random.randint(10, 99)}@okaxis"
        state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(5, 180))
            amount = round(random.uniform(1.00, 49.00), 2)
            channel = "UPI_P2P" if random.random() < 0.65 else "UPI_P2M_QR"
            bene_vpa = f"mule.cashout{random.randint(10, 99)}@paytm"

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_inr": amount,
                    "channel": channel,
                    "transaction_type": (
                        "P2P_TRANSFER" if channel == "UPI_P2P" else "QR_PAYMENT"
                    ),
                    "sender_id": sender_id,
                    "beneficiary_id": f"MULE_BEN_{random.randint(100, 999)}",
                    "sender_vpa": sender_vpa,
                    "beneficiary_vpa": bene_vpa,
                    "merchant_id": "NOT_APPLICABLE" if channel == "UPI_P2P" else "MERCH_IND_101",
                    "merchant_category": (
                        "p2p_transfer"
                        if channel == "UPI_P2P"
                        else "digital_services"
                    ),
                    "device_id": f"DEV_ATK_{random.randint(10000, 99999)}",
                    "is_new_device": 1 if random.random() < 0.70 else 0,
                    "sim_change_flag": 0,
                    "ip_location_state": state,
                    "transaction_status": "SUCCESS",
                    "is_fraud": 1,
                    "fraud_pattern": "Rapid Micro-Transfers",
                    "amount": amount,
                    "customer_id": sender_id,
                    "card_id": sender_vpa,
                    "currency": "INR",
                    "country": "IN",
                    "billing_country": "IN",
                    "bin_range": "UTIB00",
                    "segment": map_channel_to_segment(channel),
                    "ip_address": generate_simulated_ip(),
                    "pattern": "Rapid Micro-Transfers",
                }
            )
            txn_counter += 1
            generated += 1

    # ---------------------------------------------------------
    # 2. New Beneficiary Burst
    # ---------------------------------------------------------
    target = pattern_targets["New Beneficiary Burst"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(4, 7), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 600)
        )
        sender_id = f"CUST_BURST_{random.randint(100, 999)}"
        sender_vpa = f"user.compromised{random.randint(100, 999)}@okhdfcbank"
        target_bene_vpa = f"unknown.receiver{random.randint(10, 99)}@ybl"
        state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(10, 540))
            amount = round(random.uniform(490.0, 4800.0), 2)

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_inr": amount,
                    "channel": "UPI_P2P",
                    "transaction_type": "P2P_TRANSFER",
                    "sender_id": sender_id,
                    "beneficiary_id": f"BEN_NEW_{random.randint(1000, 9999)}",
                    "sender_vpa": sender_vpa,
                    "beneficiary_vpa": target_bene_vpa,
                    "merchant_id": "NOT_APPLICABLE",
                    "merchant_category": "p2p_transfer",
                    "device_id": f"DEV_BURST_{random.randint(10000, 99999)}",
                    "is_new_device": 1,
                    "sim_change_flag": 0,
                    "ip_location_state": state,
                    "transaction_status": "SUCCESS",
                    "is_fraud": 1,
                    "fraud_pattern": "New Beneficiary Burst",
                    "amount": amount,
                    "customer_id": sender_id,
                    "card_id": sender_vpa,
                    "currency": "INR",
                    "country": "IN",
                    "billing_country": "IN",
                    "bin_range": "HDFC00",
                    "segment": "UPI P2P",
                    "ip_address": generate_simulated_ip(),
                    "pattern": "New Beneficiary Burst",
                }
            )
            txn_counter += 1
            generated += 1

    # ---------------------------------------------------------
    # 3. SIM Change Takeover (SIM Swap + Account Drain)
    # ---------------------------------------------------------
    target = pattern_targets["SIM Change Takeover"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(3, 5), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 1200)
        )
        sender_id = f"CUST_SWAP_{random.randint(100, 999)}"
        sender_vpa = f"swap.victim{random.randint(100, 999)}@oksbi"
        state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(15, 900))
            amount = round(random.uniform(2000.0, 9500.0), 2)
            channel = random.choice(["UPI_P2P", "IMPS", "WALLET"])

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_inr": amount,
                    "channel": channel,
                    "transaction_type": (
                        "P2P_TRANSFER" if channel != "WALLET" else "MERCHANT_PAYMENT"
                    ),
                    "sender_id": sender_id,
                    "beneficiary_id": f"SWAP_MULE_{random.randint(100, 999)}",
                    "sender_vpa": sender_vpa,
                    "beneficiary_vpa": f"mule.drain{random.randint(10, 99)}@paytm",
                    "merchant_id": "NOT_APPLICABLE",
                    "merchant_category": "p2p_transfer",
                    "device_id": f"DEV_SWAP_{random.randint(10000, 99999)}",
                    "is_new_device": 1,
                    "sim_change_flag": 1,  # Critical signal: SIM swap
                    "ip_location_state": state,
                    "transaction_status": "SUCCESS",
                    "is_fraud": 1,
                    "fraud_pattern": "SIM Change Takeover",
                    "amount": amount,
                    "customer_id": sender_id,
                    "card_id": sender_vpa,
                    "currency": "INR",
                    "country": "IN",
                    "billing_country": "IN",
                    "bin_range": "SBIN00",
                    "segment": map_channel_to_segment(channel),
                    "ip_address": generate_simulated_ip(),
                    "pattern": "SIM Change Takeover",
                }
            )
            txn_counter += 1
            generated += 1

    # ---------------------------------------------------------
    # 4. QR Merchant Velocity Spike (Mule QR code)
    # ---------------------------------------------------------
    target = pattern_targets["QR Merchant Spike"]
    generated = 0
    while generated < target:
        batch_size = min(random.randint(12, 20), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 1800)
        )
        fake_merchant_id = f"MERCH_SPIKE_{random.randint(10, 99)}"
        fake_merchant_vpa = f"mule.qr.store{random.randint(10, 99)}@paytm"
        state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=random.randint(0, 1500))
            amount = round(random.uniform(250.0, 1850.0), 2)
            c_id = f"CUST_{random.randint(1000, 9999)}"

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_inr": amount,
                    "channel": "UPI_P2M_QR",
                    "transaction_type": "QR_PAYMENT",
                    "sender_id": c_id,
                    "beneficiary_id": fake_merchant_id,
                    "sender_vpa": f"shopper{random.randint(100, 999)}@okicici",
                    "beneficiary_vpa": fake_merchant_vpa,
                    "merchant_id": fake_merchant_id,
                    "merchant_category": "kirana_grocery",
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "is_new_device": 1 if random.random() < 0.40 else 0,
                    "sim_change_flag": 0,
                    "ip_location_state": state,
                    "transaction_status": "SUCCESS",
                    "is_fraud": 1,
                    "fraud_pattern": "QR Merchant Spike",
                    "amount": amount,
                    "customer_id": c_id,
                    "card_id": f"shopper{random.randint(100, 999)}@okicici",
                    "currency": "INR",
                    "country": "IN",
                    "billing_country": "IN",
                    "bin_range": "ICIC00",
                    "segment": "UPI P2M QR",
                    "ip_address": generate_simulated_ip(),
                    "pattern": "QR Merchant Spike",
                }
            )
            txn_counter += 1
            generated += 1

    # ---------------------------------------------------------
    # 5. Phishing Collect Request Spoofing
    # ---------------------------------------------------------
    target = pattern_targets["Phishing Collect Request"]
    generated = 0
    collect_amounts = [999.0, 1999.0, 4999.0, 9990.0, 2499.0]
    while generated < target:
        batch_size = min(random.randint(3, 6), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 3600)
        )
        victim_id = f"CUST_PHISH_{random.randint(100, 999)}"
        victim_vpa = f"victim.phish{random.randint(100, 999)}@upi"
        phisher_vpa = f"refund.support.kyc{random.randint(10, 99)}@ybl"
        state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=b * random.randint(30, 240))
            amt = random.choice(collect_amounts)

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_inr": amt,
                    "channel": "UPI_P2P",
                    "transaction_type": "COLLECT_REQUEST",
                    "sender_id": victim_id,
                    "beneficiary_id": f"PHISH_ACTOR_{random.randint(100, 999)}",
                    "sender_vpa": victim_vpa,
                    "beneficiary_vpa": phisher_vpa,
                    "merchant_id": "NOT_APPLICABLE",
                    "merchant_category": "digital_services",
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "is_new_device": 0,
                    "sim_change_flag": 0,
                    "ip_location_state": state,
                    "transaction_status": "SUCCESS",
                    "is_fraud": 1,
                    "fraud_pattern": "Phishing Collect Request",
                    "amount": amt,
                    "customer_id": victim_id,
                    "card_id": victim_vpa,
                    "currency": "INR",
                    "country": "IN",
                    "billing_country": "IN",
                    "bin_range": "PYTM01",
                    "segment": "UPI P2P",
                    "ip_address": generate_simulated_ip(),
                    "pattern": "Phishing Collect Request",
                }
            )
            txn_counter += 1
            generated += 1

    # ---------------------------------------------------------
    # 6. Structuring Split Transfers (Sub-Threshold Smurfing)
    # ---------------------------------------------------------
    target = pattern_targets["Structuring Split Transfer"]
    generated = 0
    structuring_amounts = [990.0, 995.0, 1990.0, 4950.0, 4990.0, 9900.0]
    while generated < target:
        batch_size = min(random.randint(4, 7), target - generated)
        base_time = start_time + timedelta(
            seconds=random.randint(0, total_seconds - 3600)
        )
        sender_id = f"CUST_STRUCT_{random.randint(100, 999)}"
        sender_vpa = f"struct.actor{random.randint(100, 999)}@okaxis"
        struct_amount = random.choice(structuring_amounts)
        state = np.random.choice(INDIAN_STATES, p=STATE_WEIGHTS)

        for b in range(batch_size):
            txn_time = base_time + timedelta(seconds=b * random.randint(45, 200))
            channel = "UPI_P2P" if random.random() < 0.70 else "IMPS"

            rows.append(
                {
                    "transaction_id": f"TXN_FRAUD_{txn_counter:06d}",
                    "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_inr": struct_amount,
                    "channel": channel,
                    "transaction_type": "P2P_TRANSFER",
                    "sender_id": sender_id,
                    "beneficiary_id": f"MULE_STRUCT_{random.randint(100, 999)}",
                    "sender_vpa": sender_vpa,
                    "beneficiary_vpa": f"mule.acct{random.randint(10, 99)}@kotak",
                    "merchant_id": "NOT_APPLICABLE",
                    "merchant_category": "p2p_transfer",
                    "device_id": f"DEV_{random.randint(10000, 99999)}",
                    "is_new_device": 0,
                    "sim_change_flag": 0,
                    "ip_location_state": state,
                    "transaction_status": "SUCCESS",
                    "is_fraud": 1,
                    "fraud_pattern": "Structuring Split Transfer",
                    "amount": struct_amount,
                    "customer_id": sender_id,
                    "card_id": sender_vpa,
                    "currency": "INR",
                    "country": "IN",
                    "billing_country": "IN",
                    "bin_range": "KKBK00",
                    "segment": map_channel_to_segment(channel),
                    "ip_address": generate_simulated_ip(),
                    "pattern": "Structuring Split Transfer",
                }
            )
            txn_counter += 1
            generated += 1

    return rows


def generate_dataset() -> pd.DataFrame:
    """
    Generates, sorts, formats, and validates the complete deterministic 55,000-row
    Indian digital payment transaction dataset.
    """
    # Reset random seeds
    random.seed(SEED)
    np.random.seed(SEED)

    # 1. Generate legitimate & fraud records
    legit_rows = generate_legitimate_transactions(
        NUM_LEGIT, FIXED_START_TIME, FIXED_END_TIME
    )
    fraud_rows = generate_fraud_transactions(
        NUM_FRAUD, FIXED_START_TIME, FIXED_END_TIME
    )

    all_rows = legit_rows + fraud_rows
    df = pd.DataFrame(all_rows)

    # 2. Sort chronologically by timestamp
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp_dt").reset_index(drop=True)
    df = df.drop(columns=["timestamp_dt"])

    # 3. Assign sequential deterministic transaction IDs
    df["transaction_id"] = [f"TXN_IND_{i+1:06d}" for i in range(len(df))]

    # 4. Strict Quality Checks
    assert len(df) == TOTAL_ROWS, f"Expected {TOTAL_ROWS} rows, got {len(df)}"
    assert (
        df["transaction_id"].nunique() == TOTAL_ROWS
    ), "Transaction IDs are not unique!"
    assert df["amount_inr"].min() > 0, "Non-positive transaction amount detected!"
    assert set(df["is_fraud"].unique()).issubset(
        {0, 1}
    ), "Fraud labels are not strictly binary!"
    assert df.isnull().sum().sum() == 0, "Missing values found in generated dataset!"

    return df


def main():
    print("=" * 70)
    print(" VaultGuard - Generating Indian UPI Digital Payment Dataset ")
    print("=" * 70)

    output_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "transactions.csv"

    # Backup existing legacy transactions file if not already backed up
    legacy_backup = output_dir / "transactions_backup_legacy.csv"
    if output_csv.exists() and not legacy_backup.exists():
        import shutil

        shutil.copyfile(output_csv, legacy_backup)
        print(f"[BACKUP] Preserved existing dataset to: {legacy_backup}")

    # Generate synthetic dataset
    print(f"Generating {NUM_LEGIT:,} legitimate transactions...")
    print(f"Generating {NUM_FRAUD:,} fraud transactions across 6 Indian payment patterns...")
    df = generate_dataset()

    # Save to CSV
    df.to_csv(output_csv, index=False)
    print(f"\n[SUCCESS] Saved {len(df):,} transactions to: {output_csv}\n")

    # Statistical Summary Reporting
    total_txns = len(df)
    fraud_count = int(df["is_fraud"].sum())
    legit_count = total_txns - fraud_count
    fraud_rate = (fraud_count / total_txns) * 100
    sub_1000_pct = (df["amount_inr"] < 1000.0).mean() * 100
    sub_500_pct = (df["amount_inr"] < 500.0).mean() * 100

    print("-" * 70)
    print(" DATASET SUMMARY METRICS")
    print("-" * 70)
    print(f"Total Transactions Generated : {total_txns:,}")
    print(f"Legitimate Transactions      : {legit_count:,} ({100 - fraud_rate:.2f}%)")
    print(f"Fraudulent Transactions      : {fraud_count:,} ({fraud_rate:.2f}%)")
    print(f"Transactions < INR 500 (Micro)  : {sub_500_pct:.2f}%")
    print(f"Transactions < INR 1,000 (Small): {sub_1000_pct:.2f}%")
    print(
        f"Amount Range (INR)           : INR {df['amount_inr'].min():.2f} - INR {df['amount_inr'].max():,.2f}"
    )
    print(
        f"Average Amount (INR)         : INR {df['amount_inr'].mean():.2f} (Median: INR {df['amount_inr'].median():.2f})\n"
    )

    print("-" * 70)
    print(" PAYMENT CHANNEL DISTRIBUTION")
    print("-" * 70)
    for channel, count in df["channel"].value_counts().items():
        pct = (count / total_txns) * 100
        fraud_in_chan = df[(df["channel"] == channel) & (df["is_fraud"] == 1)].shape[0]
        chan_fraud_rate = (fraud_in_chan / count) * 100
        print(
            f"- {channel:<15}: {count:>6,} txns ({pct:>5.1f}%) | Fraud: {fraud_in_chan:>4} ({chan_fraud_rate:.2f}%)"
        )

    print("\n" + "-" * 70)
    print(" FRAUD BREAKDOWN BY PATTERN")
    print("-" * 70)
    pattern_summary = (
        df[df["is_fraud"] == 1]
        .groupby("fraud_pattern")
        .agg(
            Fraud_Count=("is_fraud", "count"),
            Avg_Amount=("amount_inr", "mean"),
            Min_Amount=("amount_inr", "min"),
            Max_Amount=("amount_inr", "max"),
        )
        .reset_index()
    )
    pattern_summary["Pct_of_Total_Fraud"] = (
        pattern_summary["Fraud_Count"] / fraud_count * 100
    )

    for _, row in pattern_summary.iterrows():
        print(
            f"- {row['fraud_pattern']:<28}: {row['Fraud_Count']:>4} txns ({row['Pct_of_Total_Fraud']:>5.1f}% of fraud) | "
            f"Avg: INR {row['Avg_Amount']:>7.2f} (INR {row['Min_Amount']:.2f} - INR {row['Max_Amount']:,.2f})"
        )
    print("=" * 70)


if __name__ == "__main__":
    main()
