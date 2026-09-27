"""
VaultGuard - Database Seeder & Data Loader Service
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.orm import (
    TransactionORM,
    AlertORM,
    CustomerORM,
    MerchantORM,
    CaseORM,
)
from ml.features import engineer_features
from ml.predict import load_models, normalize_iso_score, derive_reasons, get_decision

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def seed_database_on_first_run():
    """Initializes tables and loads transactions.csv into SQLite on first run if database is empty."""
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if already seeded
        txn_count = db.query(TransactionORM).count()
        if txn_count > 0:
            print(f"[DataLoader] Database already contains {txn_count:,} transactions. Skipping initial seed.")
            return

        print("[DataLoader] Initializing database and populating transactions from data/transactions.csv...")
        csv_path = PROJECT_ROOT / "data" / "transactions.csv"
        if not csv_path.exists():
            print(f"[DataLoader WARNING] CSV file {csv_path} not found. Skipping data import.")
            return

        df = pd.read_csv(csv_path)

        # Score dataset using feature engineering & ML models
        print("[DataLoader] Scoring 55,000 transactions with hybrid XGBoost + Isolation Forest model...")
        X_df, feature_names = engineer_features(df)
        
        models = load_models()
        xgb_model = models["xgb_model"]
        iso_model = models["iso_model"]
        explainer = models["explainer"]

        xgb_probs = xgb_model.predict_proba(X_df[feature_names])[:, 1]
        iso_raw = iso_model.decision_function(X_df[feature_names])
        inv_iso = -iso_raw
        iso_min, iso_max = inv_iso.min(), inv_iso.max()
        iso_scores = (inv_iso - iso_min) / (iso_max - iso_min + 1e-5)
        iso_scores = np.clip(iso_scores, 0.0, 1.0)

        # Calculate combined scores
        risk_scores = [
            round(float(np.clip((0.75 * p + 0.25 * i) * 100.0, 0.0, 100.0)), 1)
            for p, i in zip(xgb_probs, iso_scores)
        ]
        decisions = [get_decision(rs) for rs in risk_scores]

        # Prepare ORM objects in bulk
        txn_objects = []
        customer_map = {}
        merchant_map = {}

        for idx, row in df.iterrows():
            rs = risk_scores[idx]
            dec = decisions[idx]

            # Generate top 3 reasons for suspicious / review transactions
            if rs > 40.0:
                shap_vals = explainer.shap_values(X_df.iloc[[idx]])[0]
                reasons_list = derive_reasons(X_df.iloc[idx], shap_vals, feature_names)
            else:
                reasons_list = ["Standard transaction parameters", "Verified device signature", "Low velocity"]

            status = "Approved"
            if dec == "Block":
                status = "Declined"
            elif dec == "Manual Review":
                status = "Under Review"

            txn_obj = TransactionORM(
                transaction_id=str(row["transaction_id"]),
                timestamp=str(row["timestamp"]),
                card_id=str(row["card_id"]),
                customer_id=str(row["customer_id"]),
                merchant_id=str(row["merchant_id"]),
                merchant_category=str(row["merchant_category"]),
                amount=float(row["amount"]),
                currency=str(row["currency"]),
                country=str(row["country"]),
                billing_country=str(row["billing_country"]),
                device_id=str(row["device_id"]),
                ip_address=str(row["ip_address"]),
                is_new_device=int(row["is_new_device"]),
                bin_range=str(row["bin_range"]),
                channel=str(row["channel"]),
                segment=str(row["segment"]),
                is_fraud=int(row["is_fraud"]),
                risk_score=rs,
                decision=dec,
                reasons=json.dumps(reasons_list),
                status=status,
            )
            txn_objects.append(txn_obj)

            # Aggregate Customer stats
            cust_id = str(row["customer_id"])
            if cust_id not in customer_map:
                customer_map[cust_id] = {
                    "segment": str(row["segment"]),
                    "total_transactions": 0,
                    "fraud_incidents": 0,
                    "total_spend": 0.0,
                    "max_risk": 0.0,
                }
            customer_map[cust_id]["total_transactions"] += 1
            customer_map[cust_id]["total_spend"] += float(row["amount"])
            if int(row["is_fraud"]) == 1 or dec in ["Block", "Manual Review"]:
                customer_map[cust_id]["fraud_incidents"] += 1
            if rs > customer_map[cust_id]["max_risk"]:
                customer_map[cust_id]["max_risk"] = rs

            # Aggregate Merchant stats
            merch_id = str(row["merchant_id"])
            if merch_id not in merchant_map:
                merchant_map[merch_id] = {
                    "category": str(row["merchant_category"]),
                    "total_volume": 0.0,
                    "transaction_count": 0,
                    "high_risk_count": 0,
                }
            merchant_map[merch_id]["total_volume"] += float(row["amount"])
            merchant_map[merch_id]["transaction_count"] += 1
            if rs > 60.0:
                merchant_map[merch_id]["high_risk_count"] += 1

        # Bulk insert transactions in batches of 5000
        batch_size = 5000
        for i in range(0, len(txn_objects), batch_size):
            db.bulk_save_objects(txn_objects[i : i + batch_size])
            db.commit()

        print(f"[DataLoader] Successfully loaded and scored {len(txn_objects):,} transactions.")

        # Seed Required Alerts
        seed_alerts = [
            AlertORM(
                alert_code="ALT-003",
                title="High transaction volume observed in AU debit transactions",
                segment="AU Cards",
                time_ago="10 min ago",
                status="Monitoring",
                assignee="Emily Wang",
            ),
            AlertORM(
                alert_code="ALT-002",
                title="Decline rate increase in APAC credit cards",
                segment="APAC Cards",
                time_ago="5 min ago",
                status="Investigating",
                assignee="John Lee",
            ),
            AlertORM(
                alert_code="ALT-005",
                title="System downtime affecting ME card transactions",
                segment="ME Cards",
                time_ago="20 min ago",
                status="Resolved",
                assignee="Amina Hassan",
            ),
            AlertORM(
                alert_code="ALT-008",
                title="Customer request for new features in AS card app",
                segment="AS Cards",
                time_ago="10 min ago",
                status="Pending Review",
                assignee="Mike Chen",
            ),
            AlertORM(
                alert_code="ALT-007",
                title="Issue with incorrect transaction amounts on AS card statements",
                segment="APAC Cards",
                time_ago="15 min ago",
                status="Monitoring",
                assignee="Sara Lee",
            ),
        ]
        db.add_all(seed_alerts)
        db.commit()
        print("[DataLoader] Seeded 5 initial alerts.")

        # Seed Customers
        cust_objects = []
        for c_id, info in customer_map.items():
            r_level = "Low"
            if info["fraud_incidents"] > 3 or info["max_risk"] > 70.0:
                r_level = "High"
            elif info["fraud_incidents"] > 0 or info["max_risk"] > 40.0:
                r_level = "Medium"

            cust_objects.append(
                CustomerORM(
                    customer_id=c_id,
                    segment=info["segment"],
                    risk_level=r_level,
                    total_transactions=info["total_transactions"],
                    fraud_incidents=info["fraud_incidents"],
                    total_spend=round(info["total_spend"], 2),
                )
            )
        db.bulk_save_objects(cust_objects)
        db.commit()
        print(f"[DataLoader] Seeded {len(cust_objects):,} customer profiles.")

        # Seed Merchants
        merch_objects = []
        for m_id, info in merchant_map.items():
            r_level = "Low"
            spike = round(1.0 + (info["high_risk_count"] * 0.4), 2)
            if info["high_risk_count"] > 5:
                r_level = "High"
            elif info["high_risk_count"] > 0:
                r_level = "Medium"

            merch_objects.append(
                MerchantORM(
                    merchant_id=m_id,
                    category=info["category"],
                    spike_ratio=spike,
                    risk_level=r_level,
                    total_volume=round(info["total_volume"], 2),
                    transaction_count=info["transaction_count"],
                )
            )
        db.bulk_save_objects(merch_objects)
        db.commit()
        print(f"[DataLoader] Seeded {len(merch_objects):,} merchant profiles.")

        # Seed Cases for High Risk Customers
        case_objects = []
        high_risk_customers = [c for c in cust_objects if c.risk_level == "High"][:15]
        for idx, c in enumerate(high_risk_customers, 1):
            case_objects.append(
                CaseORM(
                    case_id=f"CASE-{idx:04d}",
                    title=f"Micro-fraud Investigation for {c.customer_id}",
                    customer_id=c.customer_id,
                    risk_score=85.0 + (idx % 10),
                    status="Open" if idx % 2 == 1 else "In Review",
                    assigned_analyst="Emily Wang" if idx % 2 == 1 else "John Lee",
                )
            )
        db.bulk_save_objects(case_objects)
        db.commit()
        print(f"[DataLoader] Seeded {len(case_objects)} investigation cases.")

    finally:
        db.close()
