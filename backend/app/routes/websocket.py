"""
VaultGuard - Real-Time Simulated Transaction WebSocket Streamer
"""

import asyncio
from datetime import datetime
import json
import random
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.orm import TransactionORM
from backend.app.services.ml_service import predict_single_transaction

router = APIRouter(tags=["WebSocket Stream"])

# Active connections manager
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
    """Generates a random simulated live transaction."""
    is_fraud_scenario = random.random() < 0.25  # 25% simulated fraud in stream for live demo action

    cards = ["CARD_99212", "CARD_33104", "CARD_88192", "CARD_TEST_001", "CARD_VEL_99"]
    customers = ["CUST_1042", "CUST_9912", "CUST_4412", "CUST_SURGE_88"]
    merchants = ["MERCH_102", "MERCH_882", "MERCH_SPIKE_77"]
    categories = ["digital_goods", "retail", "gaming", "food_delivery", "subscription"]
    segments = ["EU Payments", "APAC Cards", "AU Cards", "ME Cards", "AS Cards"]

    if is_fraud_scenario:
        # Inject card testing or geo mismatch scenario
        scenario = random.choice(["card_testing", "geo_mismatch", "velocity", "high_risk_bin"])
        if scenario == "card_testing":
            amount = round(random.uniform(0.50, 4.99), 2)
            country, billing = "US", "US"
            bin_range = "411111"
        elif scenario == "geo_mismatch":
            amount = round(random.uniform(12.00, 85.00), 2)
            country, billing = "US", "RU"
            bin_range = "411111"
        elif scenario == "high_risk_bin":
            amount = round(random.uniform(5.00, 40.00), 2)
            country, billing = "DE", "DE"
            bin_range = "499999"
        else:
            amount = round(random.uniform(9.90, 49.90), 2)
            country, billing = "SG", "SG"
            bin_range = "424242"
    else:
        amount = round(random.uniform(1.50, 45.00), 2)
        country, billing = "US", "US"
        bin_range = "411111"

    txn_id = f"TXN_STREAM_{random.randint(100000, 999999)}"

    return {
        "transaction_id": txn_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "card_id": random.choice(cards),
        "customer_id": random.choice(customers),
        "merchant_id": random.choice(merchants),
        "merchant_category": random.choice(categories),
        "amount": amount,
        "currency": "USD",
        "country": country,
        "billing_country": billing,
        "device_id": f"DEV_{random.randint(10000, 99999)}",
        "ip_address": f"{random.randint(1,200)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
        "is_new_device": 1 if is_fraud_scenario else 0,
        "bin_range": bin_range,
        "channel": random.choice(["mobile_app", "web", "api"]),
        "segment": random.choice(segments),
    }


@router.websocket("/ws/transactions")
async def websocket_transactions_stream(websocket: WebSocket):
    """
    WebSocket endpoint that streams a newly scored simulated transaction every 3 seconds.
    """
    await manager.connect(websocket)
    db: Session = SessionLocal()

    try:
        while True:
            raw_txn = generate_simulated_txn()
            res = predict_single_transaction(raw_txn)

            stream_item = {
                **raw_txn,
                "risk_score": res["risk_score"],
                "decision": res["decision"],
                "reasons": res["reasons"],
                "status": "Declined" if res["decision"] == "Block" else ("Under Review" if res["decision"] == "Manual Review" else "Approved"),
            }

            # Save to database
            try:
                db_txn = TransactionORM(
                    transaction_id=stream_item["transaction_id"],
                    timestamp=stream_item["timestamp"],
                    card_id=stream_item["card_id"],
                    customer_id=stream_item["customer_id"],
                    merchant_id=stream_item["merchant_id"],
                    merchant_category=stream_item["merchant_category"],
                    amount=stream_item["amount"],
                    currency=stream_item["currency"],
                    country=stream_item["country"],
                    billing_country=stream_item["billing_country"],
                    device_id=stream_item["device_id"],
                    ip_address=stream_item["ip_address"],
                    is_new_device=stream_item["is_new_device"],
                    bin_range=stream_item["bin_range"],
                    channel=stream_item["channel"],
                    segment=stream_item["segment"],
                    is_fraud=1 if res["decision"] == "Block" else 0,
                    risk_score=res["risk_score"],
                    decision=res["decision"],
                    reasons=json.dumps(res["reasons"]),
                    status=stream_item["status"],
                )
                db.add(db_txn)
                db.commit()
            except Exception as db_err:
                db.rollback()

            await websocket.send_json(stream_item)
            await asyncio.sleep(3.0)  # Stream every 3 seconds

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
    finally:
        db.close()
