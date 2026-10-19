"""
VaultGuard - Model Management & Retraining Endpoints
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status
from backend.app.schemas.pydantic_schemas import ModelMetricsResponse
from backend.app.services.ml_service import trigger_retraining

router = APIRouter(prefix="/api/models", tags=["ML Models"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
METRICS_PATH = PROJECT_ROOT / "ml" / "saved_models" / "metrics.json"

_IS_RETRAINING = False
logger = logging.getLogger("vaultguard.models_api")


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
def retrain_models_endpoint(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
):
    """
    Triggers retraining of XGBoost + Isolation Forest pipeline on dataset.
    Protected by VAULTGUARD_ADMIN_TOKEN environment variable if configured.
    Guarded against concurrent execution to prevent file corruption.
    """
    global _IS_RETRAINING

    # Administrative token enforcement if configured
    required_token = os.getenv("VAULTGUARD_ADMIN_TOKEN")
    if required_token:
        if not x_admin_token or x_admin_token != required_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Valid administrative token required for model retraining.",
            )
    else:
        logger.warning(
            "[SECURITY AUDIT] Model retraining triggered without VAULTGUARD_ADMIN_TOKEN enforcement (dev mode)."
        )

    # Concurrency guard
    if _IS_RETRAINING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model retraining is already in progress. Please wait for completion.",
        )

    _IS_RETRAINING = True
    try:
        updated_metrics = trigger_retraining()
        return updated_metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Model retraining failed: {str(e)}"
        )
    finally:
        _IS_RETRAINING = False
