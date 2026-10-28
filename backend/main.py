import os
import joblib
from fastapi import FastAPI
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
@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "engine": "active", "version": "1.0.0"}

@app.get("/api/v1/model-info")
@app.get("/model-info")
def model_info():
    return {"version": "v1.0.0-academic", "status": "active", "models": list(models.keys())}
