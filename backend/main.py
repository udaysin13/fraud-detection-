import os
import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models = {}
model_files = {
    "logistic_regression": "backend/ml/saved_models/logistic_regression.joblib",
    "random_forest": "backend/ml/saved_models/random_forest.joblib",
    "xgboost": "backend/ml/saved_models/xgboost_model.joblib",
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

