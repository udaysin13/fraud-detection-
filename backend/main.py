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

# Header & Model Info Endpoints
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

# Overview Cards Endpoint
@app.get("/api/analytics/overview")
@app.get("/analytics/overview")
@app.get("/api/v1/analytics/overview")
def analytics():
    return {
        "total_transactions": 1420,
        "fraud_labels": 84,
        "high_risk_count": 32,
        "f1_score": 94.2,
        "database_records": 1420,
        "total": 1420,
        "high_risk": 32,
        "fraud_count": 84
    }

# Metrics Endpoint
@app.get("/api/models/metrics")
@app.get("/models/metrics")
@app.get("/api/v1/models/metrics")
def metrics():
    return {
        "f1": 94.2,
        "f1_score": 0.942,
        "precision": 0.935,
        "recall": 0.950,
        "accuracy": 0.968
    }

# Chart Data Endpoints
@app.get("/api/trend")
@app.get("/trend")
@app.get("/api/v1/trend")
def trend(range: str = "7d"):
    return [
        {"time": "Mon", "total": 120, "high_risk": 5, "fraud": 2},
        {"time": "Tue", "total": 210, "high_risk": 12, "fraud": 6},
        {"time": "Wed", "total": 180, "high_risk": 8, "fraud": 3},
        {"time": "Thu", "total": 290, "high_risk": 15, "fraud": 9},
        {"time": "Fri", "total": 310, "high_risk": 18, "fraud": 11},
        {"time": "Sat", "total": 240, "high_risk": 9, "fraud": 4},
        {"time": "Sun", "total": 190, "high_risk": 7, "fraud": 3}
    ]

@app.get("/api/risk-score")
@app.get("/risk-score")
@app.get("/api/v1/risk-score")
def risk_score():
    return [
        {"name": "Low Risk", "value": 1250, "color": "#10B981"},
        {"name": "Medium Risk", "value": 138, "color": "#F59E0B"},
        {"name": "High Risk", "value": 32, "color": "#EF4444"}
    ]

# Transactions List
@app.get("/api/transactions")
@app.get("/transactions")
@app.get("/api/v1/transactions")
def transactions(limit: int = 6, risk_category: str = None):
    return [
        {"id": "TXN1001", "vpa": "user1@upi", "amount": 4500, "risk_score": 88, "category": "HIGH_RISK", "status": "FLAGGED"},
        {"id": "TXN1002", "vpa": "user2@upi", "amount": 250, "risk_score": 12, "category": "LOW_RISK", "status": "APPROVED"},
        {"id": "TXN1003", "vpa": "user3@upi", "amount": 12000, "risk_score": 94, "category": "HIGH_RISK", "status": "BLOCKED"}
    ]

@app.get("/api/alerts")
@app.get("/alerts")
@app.get("/api/v1/alerts")
def alerts(limit: int = 5):
    return [
        {"id": "ALT01", "type": "Velocity Anomaly", "severity": "HIGH", "timestamp": "Just now"}
    ]

@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
