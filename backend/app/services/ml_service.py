"""
VaultGuard - ML Service Wrapper
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from typing import Dict, List
import pandas as pd
from ml.predict import score_transaction
from ml.train import train_models


def predict_single_transaction(txn: Dict) -> Dict:
    """Scores a single transaction dictionary using trained ML models."""
    return score_transaction(txn)


def trigger_retraining():
    """Triggers ML model pipeline training asynchronously or synchronously."""
    train_models()
    models_dir = PROJECT_ROOT / "ml" / "saved_models"
    metrics_path = models_dir / "metrics.json"

    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            return json.load(f)
    return {"status": "retrained"}
