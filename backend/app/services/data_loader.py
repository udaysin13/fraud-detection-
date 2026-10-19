"""
VaultGuard - Database Seeder & Data Loader Service

Seeds SQLite database with the Indian digital payments dataset (data/transactions.csv),
computes risk scores using the hybrid ML pipeline, establishes baseline profiles,
initializes model metadata, and creates security alerts.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import engine, Base, SessionLocal
from backend.app.models.orm import (
    TransactionORM,
    FraudAlertORM,
    AlertORM,
    ModelMetadataORM,
    CustomerORM,
    MerchantORM,
    CaseORM,
)
from ml.features import engineer_features
from ml.predict import load_models, derive_reasons, get_decision, get_risk_category

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def seed_database_on_first_run(force_reseed: bool = False):
    """
    Initializes tables and populates data/transactions.csv into SQLite.
    If force_reseed is True, clears existing tables and performs a clean import.
    """
    if force_reseed:
        print("[DataLoader] Force reseed requested. Dropping and re-creating all tables...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    else:
        Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        try:
            txn_count = db.query(TransactionORM).count()
        except Exception as schema_err:
            print(f"[DataLoader] Detected schema mismatch ({schema_err}). Re-creating all tables...")
            db.close()
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            txn_count = 0

        if txn_count > 0 and not force_reseed:
            print(f"[DataLoader] Database contains {txn_count:,} transactions. Skipping initial seed.")
            return

        print("[DataLoader] Reading Indian digital payments dataset from data/transactions.csv...")
        csv_path = PROJECT_ROOT / "data" / "transactions.csv"
        if not csv_path.exists():
            print(f"[DataLoader WARNING] CSV file {csv_path} not found. Skipping data import.")
            return

        df = pd.read_csv(csv_path)
        total_rows = len(df)
        print(f"[DataLoader] Loaded {total_rows:,} rows. Engineering point-in-time features...")

        X_df, feature_names = engineer_features(df)

        print("[DataLoader] Loading ML models (XGBoost + Isolation Forest + SHAP)...")
        models = load_models()
        xgb_model = models["xgb_model"]
        iso_model = models["iso_model"]
        explainer = models["explainer"]
        metrics = models.get("metrics", {})

        print("[DataLoader] Running batch model inference...")
        X_matrix = X_df[feature_names]
        xgb_probs = xgb_model.predict_proba(X_matrix)[:, 1]
        iso_raw = iso_model.decision_function(X_matrix)
        inv_iso = -iso_raw
        iso_min, iso_max = inv_iso.min(), inv_iso.max()
        iso_scores = (inv_iso - iso_min) / (iso_max - iso_min + 1e-5)
        iso_scores = np.clip(iso_scores, 0.0, 1.0)

        # Hybrid risk score formula: (0.75 * xgb + 0.25 * iso) * 100
        risk_scores = np.round(np.clip((0.75 * xgb_probs + 0.25 * iso_scores) * 100.0, 0.0, 100.0), 1)
        decisions = [get_decision(rs) for rs in risk_scores]
        risk_cats = [get_risk_category(rs) for rs in risk_scores]

        # Batch compute SHAP for flagged transactions to avoid slow single-row calls
        print("[DataLoader] Computing evidence explanations for suspicious transactions...")
        flagged_indices = np.where(risk_scores > 40.0)[0]
        reasons_cache = {}

        if len(flagged_indices) > 0:
            # Batch SHAP for up to 2,000 flagged items, fallback to domain rules beyond
            batch_flagged_idx = flagged_indices[:2000]
            try:
                X_flagged = X_matrix.iloc[batch_flagged_idx]
                shap_matrix = explainer.shap_values(X_flagged)
                for i, orig_idx in enumerate(batch_flagged_idx):
                    reasons_cache[orig_idx] = derive_reasons(
                        X_matrix.iloc[orig_idx], shap_matrix[i], feature_names
                    )
            except Exception as e:
                print(f"[DataLoader] Batch SHAP warning: {e}. Using domain rule explanations.")

        default_legit_reasons = [
            "Verified customer baseline parameters",
            "Established beneficiary history",
            "Standard digital transaction velocity",
        ]

        # Prepare ORM objects in bulk
        print("[DataLoader] Preparing database records...")
        txn_objects = []
        customer_map = {}
        merchant_map = {}
        fraud_alert_objects = []

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        for idx, row in df.iterrows():
            rs = float(risk_scores[idx])
            dec = decisions[idx]
            cat = risk_cats[idx]

            if idx in reasons_cache:
                reasons_list = reasons_cache[idx]
            elif rs > 40.0:
                # Fast domain rule check without SHAP matrix
                reasons_list = derive_reasons(
                    X_matrix.iloc[idx], np.zeros(len(feature_names)), feature_names
                )
            else:
                reasons_list = default_legit_reasons

            status_str = "Approved"
            if dec == "Block":
                status_str = "Declined"
            elif dec == "Manual Review":
                status_str = "Under Review"

            amt = float(row.get("amount_inr", row.get("amount", 0.0)))
            sender = str(row.get("sender_id", row.get("customer_id", "")))
            bene = str(row.get("beneficiary_id", row.get("merchant_id", "")))
            merch = str(row.get("merchant_id", "NOT_APPLICABLE"))
            seg = str(row.get("segment", "UPI P2P"))

            txn_obj = TransactionORM(
                transaction_id=str(row["transaction_id"]),
                timestamp=str(row["timestamp"]),
                amount_inr=amt,
                channel=str(row.get("channel", "UPI_P2P")),
                transaction_type=str(row.get("transaction_type", "P2P_TRANSFER")),
                sender_id=sender,
                beneficiary_id=bene,
                sender_vpa=str(row.get("sender_vpa", "")),
                beneficiary_vpa=str(row.get("beneficiary_vpa", "")),
                merchant_id=merch,
                merchant_category=str(row.get("merchant_category", "p2p_transfer")),
                device_id=str(row.get("device_id", "")),
                is_new_device=int(row.get("is_new_device", 0)),
                sim_change_flag=int(row.get("sim_change_flag", 0)),
                ip_location_state=str(row.get("ip_location_state", "")),
                transaction_status=str(row.get("transaction_status", "SUCCESS")),
                # Legacy fields for frontend compatibility
                card_id=str(row.get("card_id", sender)),
                customer_id=str(row.get("customer_id", sender)),
                amount=amt,
                currency=str(row.get("currency", "INR")),
                country=str(row.get("country", "IN")),
                billing_country=str(row.get("billing_country", "IN")),
                ip_address=str(row.get("ip_address", "")),
                bin_range=str(row.get("bin_range", "")),
                segment=seg,
                is_fraud=int(row.get("is_fraud", 0)),
                fraud_pattern=str(row.get("fraud_pattern", "")),
                # Scored outputs
                risk_score=rs,
                decision=dec,
                risk_category=cat,
                reasons=json.dumps(reasons_list),
                status=status_str,
                model_version="v1.0.0-xgb-iso-hybrid",
                scored_at=now_str,
                source="seed",
            )
            txn_objects.append(txn_obj)

            # Create FraudAlertORM for high-risk / blocked transactions
            if dec in ["Block", "Manual Review"] and len(fraud_alert_objects) < 200:
                fraud_alert_objects.append(
                    FraudAlertORM(
                        alert_id=f"FA-{row['transaction_id']}",
                        transaction_id=str(row["transaction_id"]),
                        risk_score=rs,
                        risk_category=cat,
                        reasons=json.dumps(reasons_list),
                        review_status="OPEN",
                        analyst=None,
                        model_version="v1.0.0-xgb-iso-hybrid",
                    )
                )

            # Customer statistics aggregation
            if sender not in customer_map:
                customer_map[sender] = {
                    "segment": seg,
                    "total_transactions": 0,
                    "fraud_incidents": 0,
                    "total_spend": 0.0,
                    "max_risk": 0.0,
                }
            customer_map[sender]["total_transactions"] += 1
            customer_map[sender]["total_spend"] += amt
            if int(row.get("is_fraud", 0)) == 1 or dec in ["Block", "Manual Review"]:
                customer_map[sender]["fraud_incidents"] += 1
            if rs > customer_map[sender]["max_risk"]:
                customer_map[sender]["max_risk"] = rs

            # Merchant statistics aggregation
            if merch != "NOT_APPLICABLE" and merch:
                if merch not in merchant_map:
                    merchant_map[merch] = {
                        "category": str(row.get("merchant_category", "retail")),
                        "total_volume": 0.0,
                        "transaction_count": 0,
                        "high_risk_count": 0,
                    }
                merchant_map[merch]["total_volume"] += amt
                merchant_map[merch]["transaction_count"] += 1
                if rs > 60.0:
                    merchant_map[merch]["high_risk_count"] += 1

        # Bulk insert transactions in batches
        print(f"[DataLoader] Inserting {len(txn_objects):,} transactions in batches...")
        batch_size = 5000
        for i in range(0, len(txn_objects), batch_size):
            db.bulk_save_objects(txn_objects[i : i + batch_size])
            db.commit()

        # Insert Fraud Alerts
        if fraud_alert_objects:
            db.bulk_save_objects(fraud_alert_objects)
            db.commit()

        # Seed Initial Legacy Alerts for Dashboard UI
        seed_alerts = [
            AlertORM(
                alert_code="ALT-IN-001",
                title="Suspicious SIM Swap + New Device Takeover detected on UPI P2P",
                segment="UPI P2P",
                time_ago="2 min ago",
                status="Investigating",
                assignee="Aarav Sharma",
            ),
            AlertORM(
                alert_code="ALT-IN-002",
                title="Rapid Micro-testing velocity detected on Mule QR terminal",
                segment="UPI P2M QR",
                time_ago="8 min ago",
                status="Monitoring",
                assignee="Priya Nair",
            ),
            AlertORM(
                alert_code="ALT-IN-003",
                title="High-value structuring pattern just below regulatory limit",
                segment="IMPS",
                time_ago="15 min ago",
                status="Monitoring",
                assignee="Rohan Verma",
            ),
            AlertORM(
                alert_code="ALT-IN-004",
                title="Sudden merchant terminal volume spike (3.8x baseline)",
                segment="UPI P2M QR",
                time_ago="25 min ago",
                status="Investigating",
                assignee="Sneha Patel",
            ),
            AlertORM(
                alert_code="ALT-IN-005",
                title="Off-hours high-velocity collect requests blocked",
                segment="Digital Wallet",
                time_ago="40 min ago",
                status="Resolved",
                assignee="Aarav Sharma",
            ),
        ]
        db.add_all(seed_alerts)
        db.commit()

        # Seed Model Metadata
        model_meta = ModelMetadataORM(
            model_name=metrics.get("selected_model", "XGBoost Classifier"),
            model_version="v1.0.0-xgb-iso-hybrid",
            training_timestamp=now_str,
            selected_threshold=metrics.get("selected_threshold", 0.57),
            precision=metrics.get("precision", 0.9889),
            recall=metrics.get("recall", 0.9834),
            f1_score=metrics.get("f1_score", 0.9861),
            roc_auc=metrics.get("roc_auc", 1.0),
            pr_auc=metrics.get("pr_auc", 0.9986),
            test_sample_count=metrics.get("test_sample_count", 8250),
            fraud_count_test=metrics.get("fraud_count_test", 181),
            feature_count=len(feature_names),
            is_active=1,
        )
        db.add(model_meta)
        db.commit()

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

        # Seed Investigation Cases
        case_objects = []
        high_risk_custs = [c for c in cust_objects if c.risk_level == "High"][:15]
        for idx, c in enumerate(high_risk_custs, 1):
            case_objects.append(
                CaseORM(
                    case_id=f"CASE-IN-{idx:04d}",
                    title=f"UPI Micro-fraud Investigation for {c.customer_id}",
                    customer_id=c.customer_id,
                    risk_score=85.0 + (idx % 10),
                    status="Open" if idx % 2 == 1 else "In Review",
                    assigned_analyst="Aarav Sharma" if idx % 2 == 1 else "Priya Nair",
                )
            )
        db.bulk_save_objects(case_objects)
        db.commit()

        print(f"[DataLoader] Successfully seeded database with {len(txn_objects):,} transactions, "
              f"{len(cust_objects):,} customers, and {len(merch_objects):,} merchants.")

    finally:
        db.close()


if __name__ == "__main__":
    print("Running explicit database re-seed...")
    seed_database_on_first_run(force_reseed=True)
