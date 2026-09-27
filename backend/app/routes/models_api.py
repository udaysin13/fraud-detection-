"""
VaultGuard - Model Management & Retraining Endpoints
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.app.schemas.pydantic_schemas import ModelMetricsResponse
from backend.app.services.ml_service import trigger_retraining

router = APIRouter(prefix="/api/models", tags=["ML Models"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
METRICS_PATH = PROJECT_ROOT / "ml" / "saved_models" / "metrics.json"


@router.get("/metrics", response_model=ModelMetricsResponse)
def get_model_metrics():
    """
    Returns performance metrics (Precision, Recall, F1, ROC-AUC, Confusion Matrix)
    for the deployed hybrid ML models.
    """
    if not METRICS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Model metrics file not found. Please train models first.",
        )

    with open(METRICS_PATH, "r") as f:
        metrics_data = json.load(f)

    return metrics_data


@router.post("/retrain", response_model=ModelMetricsResponse)
def retrain_models_endpoint():
    """
    Triggers complete retraining of XGBoost + Isolation Forest pipeline on dataset
    and returns updated metrics.
    """
    try:
        updated_metrics = trigger_retraining()
        return updated_metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Model retraining failed: {str(e)}"
        )
