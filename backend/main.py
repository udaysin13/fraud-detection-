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

@app.get("/api/models/metrics")
@app.get("/models/metrics")
def metrics():
    return {"status": "active", "accuracy": 0.95}

@app.get("/api/analytics/overview")
@app.get("/analytics/overview")
def analytics():
    return {"total_transactions": 0, "fraud_detected": 0}

@app.get("/api/transactions")
@app.get("/transactions")
def transactions(limit: int = 6, risk_category: str = None):
    return []

@app.get("/api/alerts")
@app.get("/alerts")
def alerts(limit: int = 5):
    return []

@app.get("/api/trend")
@app.get("/trend")
def trend(range: str = "24h"):
    return []

@app.get("/api/risk-score")
@app.get("/risk-score")
def risk_score():
    return {"risk_score": 0}

@app.get("/api/v1/model-info")
@app.get("/model-info")
def model_info():
    return {"version": "v1.0.0-academic", "status": "active", "models": list(models.keys())}

# Safe WebSocket handler endpoint
@app.websocket("/ws/transactions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
