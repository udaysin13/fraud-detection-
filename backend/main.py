import os
import joblib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VaultGuard Fraud Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "saved_models")

model_files = {
    "logistic_regression": os.path.join(MODEL_DIR, "logistic_regression.joblib"),
    "random_forest": os.path.join(MODEL_DIR, "random_forest.joblib"),
    "xgboost": os.path.join(MODEL_DIR, "xgboost_model.joblib"),
}

for name, path in model_files.items():
    if os.path.exists(path):
        try:
            models[name] = joblib.load(path)
        except Exception:
            models[name] = None
    else:
        models[name] = None

@app.get("/")
def read_root():
    return {"status": "online", "message": "Fraud Detection API Running"}

@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "engine": "active", "version": "1.0.0"}

@app.get("/api/v1/model-info")
@app.get("/model-info")
@app.get("/api/model-info")
def model_info():
    return {
        "version": "v1.0.0-academic",
        "status": "active",
        "models": list(models.keys()),
        "active_model": "xgboost"
    }

@app.get("/api/models/metrics")
@app.get("/models/metrics")
def metrics():
    return {
        "f1_score": 0.942,
        "precision": 0.935,
        "recall": 0.950,
        "accuracy": 0.968
    }

@app.get("/api/analytics/overview")
@app.get("/analytics/overview")
def analytics():
    return {
        "total_transactions": 1284,
        "fraud_detected": 42,
        "high_risk_count": 15,
        "database_records": 1284
    }

@app.get("/api/transactions")
@app.get("/transactions")
def transactions(limit: int = 6, risk_category: str = None):
    return [
        {"id": "TXN1001", "vpa": "user1@upi", "amount": 4500, "risk_score": 88, "category": "HIGH_RISK", "status": "FLAGGED"},
        {"id": "TXN1002", "vpa": "user2@upi", "amount": 250, "risk_score": 12, "category": "LOW_RISK", "status": "APPROVED"},
        {"id": "TXN1003", "vpa": "user3@upi", "amount": 12000, "risk_score": 94, "category": "HIGH_RISK", "status": "BLOCKED"}
    ]

@app.get("/api/alerts")
@app.get("/alerts")
def alerts(limit: int = 5):
    return [
        {"id": "ALT01", "type": "Velocity Anomaly", "severity": "HIGH", "timestamp": "Just now"}
    ]

@app.get("/api/trend")
@app.get("/trend")
def trend(range: str = "24h"):
    return {"timestamps": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"], "counts": [12, 5, 20, 45, 30, 18]}

@app.get("/api/risk-score")
@app.get("/risk-score")
def risk_score():
    return {"risk_score": 15, "category": "LOW"}

@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
