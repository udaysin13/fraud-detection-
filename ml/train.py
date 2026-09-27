"""
VaultGuard - Small Transaction Fraud Detection System
ml/train.py

Trains Isolation Forest (unsupervised) and XGBoost (supervised) models.
Combines scores into a 0-100 risk score with decision thresholds.
Saves models, SHAP explainer, and performance metrics to ml/saved_models/.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import shap

from ml.features import FEATURE_COLUMNS, engineer_features

SEED = 42


def normalize_iso_score(scores):
    """
    Normalizes Isolation Forest decision_function scores into a 0.0 to 1.0 anomaly scale.
    Lower raw decision score = higher anomaly.
    """
    # Inverse score so higher value means higher anomaly risk
    inv_scores = -scores
    min_val, max_val = inv_scores.min(), inv_scores.max()
    if max_val == min_val:
        return np.zeros_like(scores)
    norm_scores = (inv_scores - min_val) / (max_val - min_val)
    return np.clip(norm_scores, 0.0, 1.0)


def compute_risk_score(xgb_prob, iso_score):
    """
    Combines XGBoost fraud probability (75% weight) and Isolation Forest anomaly score (25% weight)
    into a final 0 to 100 risk score.
    """
    combined = (0.75 * xgb_prob) + (0.25 * iso_score)
    risk_score = np.round(combined * 100.0, 1)
    return np.clip(risk_score, 0.0, 100.0)


def get_decision(risk_score):
    """Maps risk score (0-100) to business decisions: Allow, Manual Review, or Block."""
    if risk_score <= 40.0:
        return "Allow"
    elif risk_score <= 70.0:
        return "Manual Review"
    else:
        return "Block"


def train_models():
    print("=" * 60)
    print(" VaultGuard - Training Fraud Detection Machine Learning Pipeline ")
    print("=" * 60)

    # 1. Load Data
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "data" / "transactions.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. Please run ml/generate_data.py first."
        )

    print(f"Loading transaction dataset from: {csv_path}")
    raw_df = pd.read_csv(csv_path)

    # 2. Engineer Features
    print("Engineering domain features (velocity, z-scores, device surges, structuring)...")
    X, feature_names = engineer_features(raw_df)
    y = raw_df["is_fraud"].values

    print(f"Engineered {X.shape[1]} features across {X.shape[0]:,} transactions.")

    # 3. Stratified Train/Test Split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=SEED, stratify=y
    )

    print(
        f"Train set: {X_train.shape[0]:,} samples | Test set: {X_test.shape[0]:,} samples"
    )
    print(
        f"Train fraud rate: {y_train.mean()*100:.2f}% | Test fraud rate: {y_test.mean()*100:.2f}%"
    )

    # 4. Train Supervised XGBoost Classifier with Class Weighting
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / max(1, pos_count)

    print(
        f"\nTraining XGBoost Classifier (scale_pos_weight: {scale_pos_weight:.2f})..."
    )
    xgb_model = XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=SEED,
        eval_metric="logloss",
    )
    xgb_model.fit(X_train, y_train)

    # 5. Train Unsupervised Isolation Forest
    print("Training Isolation Forest Anomaly Detector...")
    iso_model = IsolationForest(
        n_estimators=100,
        contamination=0.02,
        random_state=SEED,
        n_jobs=-1,
    )
    iso_model.fit(X_train)

    # 6. Evaluate on Test Set
    print("\nEvaluating model performance on test set...")
    xgb_probs_test = xgb_model.predict_proba(X_test)[:, 1]
    iso_raw_test = iso_model.decision_function(X_test)
    iso_scores_test = normalize_iso_score(iso_raw_test)

    # Calculate combined risk score
    risk_scores_test = compute_risk_score(xgb_probs_test, iso_scores_test)
    binary_preds = (risk_scores_test >= 41.0).astype(int)

    # Calculate metrics
    precision = float(precision_score(y_test, binary_preds))
    recall = float(recall_score(y_test, binary_preds))
    f1 = float(f1_score(y_test, binary_preds))
    roc_auc = float(roc_auc_score(y_test, xgb_probs_test))
    cm = confusion_matrix(y_test, binary_preds).tolist()

    # Decision Breakdown
    decisions = [get_decision(score) for score in risk_scores_test]
    decision_counts = pd.Series(decisions).value_counts().to_dict()

    print("\n" + "-" * 60)
    print(" EVALUATION METRICS (TEST SET)")
    print("-" * 60)
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1 Score  : {f1:.4f}")
    print(f"ROC-AUC   : {roc_auc:.4f}")
    print(f"Confusion Matrix [TN, FP / FN, TP]:")
    print(f"  [{cm[0][0]:>5}, {cm[0][1]:>5}]")
    print(f"  [{cm[1][0]:>5}, {cm[1][1]:>5}]")

    print("\nDecision Distribution on Test Set:")
    for dec, cnt in decision_counts.items():
        pct = (cnt / len(decisions)) * 100
        print(f"  • {dec:<15}: {cnt:>5} ({pct:.2f}%)")

    # 7. Initialize SHAP Explainer
    print("\nBuilding SHAP TreeExplainer for real-time explainability...")
    explainer = shap.TreeExplainer(xgb_model)

    # 8. Save Models & Artifacts
    models_dir = project_root / "ml" / "saved_models"
    models_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(xgb_model, models_dir / "xgboost_model.joblib")
    joblib.dump(iso_model, models_dir / "isolation_forest.joblib")
    joblib.dump(explainer, models_dir / "shap_explainer.joblib")
    joblib.dump(feature_names, models_dir / "feature_names.joblib")

    metrics_payload = {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "confusion_matrix": cm,
        "test_sample_count": len(y_test),
        "fraud_count_test": int(y_test.sum()),
        "decision_distribution": decision_counts,
        "feature_columns": feature_names,
    }

    with open(models_dir / "metrics.json", "w") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\n[SUCCESS] Saved all models and metrics to: {models_dir}")
    print("=" * 60)


if __name__ == "__main__":
    train_models()
