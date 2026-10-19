"""
VaultGuard - Real-Time Indian Payment WebSocket Streamer

Streams simulated Indian digital payment transactions (UPI P2P, UPI P2M QR, Wallets)
scored in real-time through the hybrid ML engine with database persistence.
"""

import asyncio
from datetime import datetime, timezone
import json
import random
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.orm import TransactionORM, AlertORM, FraudAlertORM
from backend.app.services.ml_service import predict_single_transaction

router = APIRouter(tags=["WebSocket Stream"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


def generate_simulated_txn():
    """Generates a realistic simulated Indian digital payment transaction."""
    is_fraud_scenario = random.random() < 0.20  # 20% simulated fraud in stream

    vpa_handles = ["okhdfcbank", "paytm", "okicici", "okaxis", "barodampay", "ibl"]
    first_names = ["aarav", "priya", "rohan", "sneha", "vikram", "ananya", "karthik", "pooja", "rahul", "neha"]
    last_names = ["sharma", "patel", "verma", "nair", "gupta", "kulkarni", "reddy", "joshi", "mehta", "chatterjee"]
    states = ["Maharashtra", "Karnataka", "Delhi", "Uttar Pradesh", "Gujarat", "Tamil Nadu", "Telangana", "West Bengal"]

    sender_name = f"{random.choice(first_names)}.{random.choice(last_names)}{random.randint(10, 99)}"
    sender_vpa = f"{sender_name}@{random.choice(vpa_handles)}"
    sender_id = f"CUST_IND_{random.randint(1000, 9999)}"

    channels = ["UPI_P2P", "UPI_P2M_QR", "WALLET", "IMPS"]
    channel = random.choice(channels)

    if channel == "UPI_P2M_QR":
        txn_type = "MERCHANT_PAYMENT"
        categories = ["kirana_grocery", "food_dining", "retail_fashion", "pharmacy_health", "electronics"]
        category = random.choice(categories)
        merch_id = f"MERCH_IND_{random.randint(100, 150)}"
        beneficiary_id = merch_id
        beneficiary_vpa = f"{category.split('_')[0]}.store@{random.choice(vpa_handles)}"
    else:
        txn_type = "P2P_TRANSFER"
        category = "p2p_transfer"
        merch_id = "NOT_APPLICABLE"
        bene_name = f"{random.choice(first_names)}.{random.choice(last_names)}{random.randint(10, 99)}"
        beneficiary_id = f"BEN_IND_{random.randint(1000, 5000)}"
        beneficiary_vpa = f"{bene_name}@{random.choice(vpa_handles)}"

    device_id = f"DEV_IND_{random.randint(10000, 20000)}"
    sim_change_flag = 0
    is_new_device = 0

    if is_fraud_scenario:
        scenario = random.choice(["account_takeover", "micro_testing", "structuring", "mule_spike"])
        if scenario == "account_takeover":
            amount = round(random.uniform(4500.0, 9800.0), 2)
            sim_change_flag = 1
            is_new_device = 1
        elif scenario == "micro_testing":
            amount = round(random.uniform(1.0, 25.0), 2)
            is_new_device = 1
        elif scenario == "structuring":
            amount = round(random.choice([999.0, 1990.0, 4950.0, 9900.0]), 2)
        else:  # mule_spike
            amount = round(random.uniform(500.0, 2500.0), 2)
            channel = "UPI_P2M_QR"
            txn_type = "MERCHANT_PAYMENT"
            category = "digital_services"
            merch_id = "MERCH_IND_112"
            beneficiary_id = merch_id
    else:
        amount = round(random.uniform(15.0, 850.0), 2)

    txn_id = f"TXN_WS_{int(time.time() * 1000) % 1000000:06d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "transaction_id": txn_id,
        "timestamp": now_str,
        "amount_inr": amount,
        "channel": channel,
        "transaction_type": txn_type,
        "sender_id": sender_id,
        "beneficiary_id": beneficiary_id,
        "sender_vpa": sender_vpa,
        "beneficiary_vpa": beneficiary_vpa,
        "merchant_id": merch_id,
        "merchant_category": category,
        "device_id": device_id,
        "is_new_device": is_new_device,
        "sim_change_flag": sim_change_flag,
        "ip_location_state": random.choice(states),
        # Legacy compatibility aliases
        "amount": amount,
        "customer_id": sender_id,
        "card_id": sender_vpa,
        "currency": "INR",
        "country": "IN",
        "billing_country": "IN",
        "ip_address": f"{random.randint(27, 157)}.{random.randint(10, 200)}.{random.randint(10, 200)}.{random.randint(1, 254)}",
        "bin_range": "UPI000",
        "segment": "UPI Payments",
    }


@router.websocket("/ws/transactions")
async def websocket_transactions_stream(websocket: WebSocket):
    """
    WebSocket endpoint streaming newly scored transactions every 3 seconds.
    """
    await manager.connect(websocket)

    try:
        while True:
            raw_txn = generate_simulated_txn()
            
            # Use a fresh database session for each tick to prevent stale connection drops
            db: Session = SessionLocal()
            try:
                res = predict_single_transaction(raw_txn, db=db)
            except Exception as inner_e:
                print(f"[WebSocket Prediction Error]: {inner_e}")
                res = {
                    "risk_score": 15.0,
                    "decision": "Approve",
                    "risk_category": "LOW_RISK",
                    "reasons": ["Fallback simulation active"],
                    "xgb_probability": 0.05,
                    "anomaly_score": 0.1
                }
            finally:
                db.close()

            decision = res.get("decision", "Approve")
            status_str = "Approved"
            if decision == "Block":
                status_str = "Declined"
            elif decision == "Manual Review":
                status_str = "Under Review"

            stream_item = {
                **raw_txn,
                "risk_score": res.get("risk_score", 0.0),
                "decision": decision,
                "risk_category": res.get("risk_category", "LOW_RISK"),
                "reasons": res.get("reasons", []),
                "status": status_str,
                "xgb_probability": res.get("xgb_probability", 0.0),
                "anomaly_score": res.get("anomaly_score", 0.0),
                "is_simulated": True,
                "source": "websocket_simulation",
            }

            await websocket.send_json(stream_item)
            await asyncio.sleep(3.0)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket Disconnect Error]: {e}")
        manager.disconnect(websocket)