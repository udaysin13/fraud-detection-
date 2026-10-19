"""
VaultGuard - Indian Digital Payment Fraud Detection System
ml/train.py

Leakage-safe machine learning training and evaluation pipeline:
1. Chronological splitting: Train (70%), Validation (15%), Test (15%).
2. Preprocessing fitted on training split only.
3. Multi-model benchmarking: Logistic Regression (baseline), Random Forest,
   XGBoost Classifier, and Isolation Forest (unsupervised).
4. Validation-based threshold tuning (maximizing F1-score on validation set only).
5. Final evaluation on untouched test set with PR-AUC, ROC-AUC, Precision, Recall,
   F1-score, and Confusion Matrices.
6. Serialization of trained models, SHAP TreeExplainer, and structured metrics.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe UTF-8 output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ml.features import FEATURE_COLUMNS, engineer_features

SEED = 42
np.random.seed(SEED)

MODELS_DIR = PROJECT_ROOT / "ml" / "saved_models"


def split_chronological(
    df: pd.DataFrame, train_ratio: float = 0.70, val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits a DataFrame chronologically based on row order (assumed sorted by timestamp).
    Returns (train_df, val_df, test_df).
    """
    total = len(df)
    train_end = int(total * train_ratio)
    val_end = int(total * (train_ratio + val_ratio))
    return df.iloc[:train_end].copy(), df.iloc[train_end:val_end].copy(), df.iloc[val_end:].copy()


def tune_decision_threshold(
    y_val: np.ndarray, val_scores: np.ndarray
) -> Tuple[float, float]:
    """
    Finds the decision threshold that maximizes F1-score on the validation set only.
    Prevents threshold overfitting on the test set.

    Returns:
        best_threshold (float): Selected decision threshold
        best_f1 (float): F1-score achieved on validation data
    """
    best_threshold = 0.50
    best_f1 = 0.0

    # Sweep thresholds from 0.05 to 0.95
    for candidate in np.linspace(0.05, 0.95, 91):
        preds = (val_scores >= candidate).astype(int)
        score = f1_score(y_val, preds, zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_threshold = float(candidate)

    return round(best_threshold, 4), round(best_f1, 4)


def evaluate_predictions(
    y_true: np.ndarray,
    probs: np.ndarray,
    threshold: float,
    split_name: str = "Test",
) -> Dict:
    """Computes comprehensive evaluation metrics for a model's predicted probabilities, safely handling single-class edge cases."""
    preds = (probs >= threshold).astype(int)

    precision = float(precision_score(y_true, preds, zero_division=0))
    recall = float(recall_score(y_true, preds, zero_division=0))
    f1 = float(f1_score(y_true, preds, zero_division=0))

    try:
        pr_auc = float(average_precision_score(y_true, probs))
        if np.isnan(pr_auc):
            pr_auc = 0.0
    except Exception:
        pr_auc = 0.0

    try:
        if len(np.unique(y_true)) > 1:
            roc_auc = float(roc_auc_score(y_true, probs))
            if np.isnan(roc_auc):
                roc_auc = 0.0
        else:
            roc_auc = 0.0
    except Exception:
        roc_auc = 0.0

    cm = confusion_matrix(y_true, preds).tolist()
    if len(cm) == 1:
        # Only one class present in y_true
        if y_true[0] == 0:
            tn = int(cm[0][0]) if len(cm[0]) > 0 else 0
            fp = int(cm[0][1]) if len(cm[0]) > 1 else 0
            fn, tp = 0, 0
        else:
            tp = int(cm[0][0]) if len(cm[0]) > 0 else 0
            fn = int(cm[0][1]) if len(cm[0]) > 1 else 0
            tn, fp = 0, 0
    else:
        fp = int(cm[0][1])
        fn = int(cm[1][0])
        tp = int(cm[1][1])
        tn = int(cm[0][0])

    return {
        "split": split_name,
        "sample_count": len(y_true),
        "fraud_count": int(y_true.sum()),
        "fraud_prevalence_pct": round(float(y_true.mean() * 100), 2),
        "threshold": round(float(threshold), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "confusion_matrix": cm,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
    }


def normalize_iso_scores(
    raw_scores: np.ndarray, min_val: float, max_val: float
) -> np.ndarray:
    """Normalizes Isolation Forest decision scores to a 0.0 to 1.0 anomaly scale."""
    inv = -raw_scores
    diff = max_val - min_val
    if diff <= 1e-7:
        return np.zeros_like(raw_scores)
    norm = (inv - min_val) / diff
    return np.clip(norm, 0.0, 1.0)


def compute_risk_score(prob: float, anomaly_score: float = 0.0) -> float:
    """Combines supervised fraud probability (75%) and anomaly score (25%) into a 0-100 risk score."""
    combined = (0.75 * prob) + (0.25 * anomaly_score)
    return round(float(np.clip(combined * 100.0, 0.0, 100.0)), 1)


def get_decision(risk_score: float) -> str:
    """Maps 0-100 risk score to business assistance categories: Allow, Manual Review, Block."""
    if risk_score <= 40.0:
        return "Allow"
    elif risk_score <= 70.0:
        return "Manual Review"
    else:
        return "Block"


def train_models():
    print("=" * 70)
    print(" VaultGuard - Leakage-Safe Indian Digital Payment ML Pipeline ")
    print("=" * 70)

    # 1. Load Dataset
    csv_path = PROJECT_ROOT / "data" / "transactions.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. Please run ml/generate_data.py first."
        )

    print(f"Loading transactions dataset from: {csv_path}")
    raw_df = pd.read_csv(csv_path)

    # 2. Point-in-Time Feature Engineering
    print("Engineering domain features (velocity, SIM/device flags, merchant spikes)...")
    X, feature_names = engineer_features(raw_df)
    y = raw_df["is_fraud"].values

    total_samples = len(raw_df)
    print(f"Engineered {X.shape[1]} features across {total_samples:,} transactions.")

    # 3. Chronological Dataset Split: Train (70%), Validation (15%), Test (15%)
    train_end = int(total_samples * 0.70)  # 38,500
    val_end = int(total_samples * 0.85)    # 46,750

    X_train, y_train = X.iloc[:train_end].copy(), y[:train_end]
    X_val, y_val = X.iloc[train_end:val_end].copy(), y[train_end:val_end]
    X_test, y_test = X.iloc[val_end:].copy(), y[val_end:]

    train_dates = (raw_df["timestamp"].iloc[0], raw_df["timestamp"].iloc[train_end - 1])
    val_dates = (raw_df["timestamp"].iloc[train_end], raw_df["timestamp"].iloc[val_end - 1])
    test_dates = (raw_df["timestamp"].iloc[val_end], raw_df["timestamp"].iloc[-1])

    print("\n" + "-" * 70)
    print(" CHRONOLOGICAL SPLIT SUMMARY (ZERO TEMPORAL LEAKAGE)")
    print("-" * 70)
    print(
        f"Train Split (70%) : {len(X_train):>6,} txns | Fraud: {y_train.sum():>4} ({y_train.mean()*100:.2f}%) | {train_dates[0]} to {train_dates[1]}"
    )
    print(
        f"Val Split   (15%) : {len(X_val):>6,} txns | Fraud: {y_val.sum():>4} ({y_val.mean()*100:.2f}%) | {val_dates[0]} to {val_dates[1]}"
    )
    print(
        f"Test Split  (15%) : {len(X_test):>6,} txns | Fraud: {y_test.sum():>4} ({y_test.mean()*100:.2f}%) | {test_dates[0]} to {test_dates[1]}"
    )

    # Verify both classes exist in all splits
    for name, split_y in [("Train", y_train), ("Val", y_val), ("Test", y_test)]:
        if split_y.sum() == 0 or split_y.sum() == len(split_y):
            raise ValueError(f"Split {name} contains only a single class! Cannot evaluate.")

    # 4. Learned Preprocessing: StandardScaler fitted on X_train ONLY
    print("\nFitting StandardScaler on training data only...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Dictionary to collect all benchmark model outputs
    model_benchmarks = {}

    # ---------------------------------------------------------
    # Model 1: Logistic Regression (Baseline)
    # ---------------------------------------------------------
    print("\n[1/4] Training Logistic Regression Baseline (class_weight='balanced')...")
    lr_model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=SEED,
        solver="lbfgs",
    )
    lr_model.fit(X_train_scaled, y_train)

    lr_val_probs = lr_model.predict_proba(X_val_scaled)[:, 1]
    lr_thresh, lr_val_f1 = tune_decision_threshold(y_val, lr_val_probs)
    lr_test_probs = lr_model.predict_proba(X_test_scaled)[:, 1]
    lr_test_eval = evaluate_predictions(y_test, lr_test_probs, lr_thresh, "Test")

    model_benchmarks["logistic_regression"] = {
        "model_type": "Logistic Regression (StandardScaler + Balanced Weights)",
        "val_threshold": lr_thresh,
        "val_f1": lr_val_f1,
        "val_pr_auc": round(float(average_precision_score(y_val, lr_val_probs)), 4),
        "val_roc_auc": round(float(roc_auc_score(y_val, lr_val_probs)), 4),
        "test_metrics": lr_test_eval,
    }
    print(
        f"      Val PR-AUC: {model_benchmarks['logistic_regression']['val_pr_auc']} | Val F1: {lr_val_f1} (T={lr_thresh})"
    )
    print(
        f"      Test PR-AUC: {lr_test_eval['pr_auc']} | Test Recall: {lr_test_eval['recall']} | Test Prec: {lr_test_eval['precision']}"
    )

    # ---------------------------------------------------------
    # Model 2: Random Forest Classifier
    # ---------------------------------------------------------
    print("\n[2/4] Training Random Forest Classifier (n_estimators=100, max_depth=10)...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )
    rf_model.fit(X_train, y_train)

    rf_val_probs = rf_model.predict_proba(X_val)[:, 1]
    rf_thresh, rf_val_f1 = tune_decision_threshold(y_val, rf_val_probs)
    rf_test_probs = rf_model.predict_proba(X_test)[:, 1]
    rf_test_eval = evaluate_predictions(y_test, rf_test_probs, rf_thresh, "Test")

    model_benchmarks["random_forest"] = {
        "model_type": "Random Forest (Balanced Weights, 100 Trees, Depth 10)",
        "val_threshold": rf_thresh,
        "val_f1": rf_val_f1,
        "val_pr_auc": round(float(average_precision_score(y_val, rf_val_probs)), 4),
        "val_roc_auc": round(float(roc_auc_score(y_val, rf_val_probs)), 4),
        "test_metrics": rf_test_eval,
    }
    print(
        f"      Val PR-AUC: {model_benchmarks['random_forest']['val_pr_auc']} | Val F1: {rf_val_f1} (T={rf_thresh})"
    )
    print(
        f"      Test PR-AUC: {rf_test_eval['pr_auc']} | Test Recall: {rf_test_eval['recall']} | Test Prec: {rf_test_eval['precision']}"
    )

    # ---------------------------------------------------------
    # Model 3: XGBoost Classifier (Primary Supervised)
    # ---------------------------------------------------------
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / max(1, pos_count)

    print(
        f"\n[3/4] Training XGBoost Classifier (scale_pos_weight={scale_pos_weight:.2f}, depth=5)..."
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

    xgb_val_probs = xgb_model.predict_proba(X_val)[:, 1]
    xgb_thresh, xgb_val_f1 = tune_decision_threshold(y_val, xgb_val_probs)
    xgb_test_probs = xgb_model.predict_proba(X_test)[:, 1]
    xgb_test_eval = evaluate_predictions(y_test, xgb_test_probs, xgb_thresh, "Test")

    model_benchmarks["xgboost"] = {
        "model_type": "XGBoost Classifier (Class-Weighted, 150 Trees, Depth 5)",
        "val_threshold": xgb_thresh,
        "val_f1": xgb_val_f1,
        "val_pr_auc": round(float(average_precision_score(y_val, xgb_val_probs)), 4),
        "val_roc_auc": round(float(roc_auc_score(y_val, xgb_val_probs)), 4),
        "test_metrics": xgb_test_eval,
    }
    print(
        f"      Val PR-AUC: {model_benchmarks['xgboost']['val_pr_auc']} | Val F1: {xgb_val_f1} (T={xgb_thresh})"
    )
    print(
        f"      Test PR-AUC: {xgb_test_eval['pr_auc']} | Test Recall: {xgb_test_eval['recall']} | Test Prec: {xgb_test_eval['precision']}"
    )

    # ---------------------------------------------------------
    # Model 4: Isolation Forest (Unsupervised Comparison)
    # ---------------------------------------------------------
    print("\n[4/4] Training Isolation Forest (Unsupervised Anomaly Baseline)...")
    iso_model = IsolationForest(
        n_estimators=100,
        contamination=0.02,
        random_state=SEED,
        n_jobs=-1,
    )
    iso_model.fit(X_train)

    # Fit score normalization parameters on train set ONLY
    iso_raw_train = -iso_model.decision_function(X_train)
    iso_min = float(iso_raw_train.min())
    iso_max = float(iso_raw_train.max())

    iso_val_raw = iso_model.decision_function(X_val)
    iso_val_norm = normalize_iso_scores(iso_val_raw, iso_min, iso_max)
    iso_thresh, iso_val_f1 = tune_decision_threshold(y_val, iso_val_norm)

    iso_test_raw = iso_model.decision_function(X_test)
    iso_test_norm = normalize_iso_scores(iso_test_raw, iso_min, iso_max)
    iso_test_eval = evaluate_predictions(y_test, iso_test_norm, iso_thresh, "Test")

    model_benchmarks["isolation_forest"] = {
        "model_type": "Isolation Forest (Unsupervised Anomaly Detector)",
        "val_threshold": iso_thresh,
        "val_f1": iso_val_f1,
        "val_pr_auc": round(float(average_precision_score(y_val, iso_val_norm)), 4),
        "val_roc_auc": round(float(roc_auc_score(y_val, iso_val_norm)), 4),
        "test_metrics": iso_test_eval,
    }
    print(
        f"      Val PR-AUC: {model_benchmarks['isolation_forest']['val_pr_auc']} | Val F1: {iso_val_f1} (T={iso_thresh})"
    )
    print(
        f"      Test PR-AUC: {iso_test_eval['pr_auc']} | Test Recall: {iso_test_eval['recall']} | Test Prec: {iso_test_eval['precision']}"
    )

    # ---------------------------------------------------------
    # Model Comparison Summary Table
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print(" MODEL BENCHMARK COMPARISON ON UNTOUCHED TEST SET")
    print("=" * 70)
    print(
        f"{'Model':<22} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'F1-Score':<8} | {'Recall':<8} | {'Precision':<9} | {'T*':<6}"
    )
    print("-" * 75)
    for key, info in model_benchmarks.items():
        tm = info["test_metrics"]
        print(
            f"{key:<22} | {tm['pr_auc']:<8.4f} | {tm['roc_auc']:<8.4f} | {tm['f1_score']:<8.4f} | "
            f"{tm['recall']:<8.4f} | {tm['precision']:<9.4f} | {info['val_threshold']:<6.2f}"
        )
    print("=" * 70)

    # 5. Hybrid Risk Scoring on Test Set
    risk_scores_test = [
        compute_risk_score(p, a)
        for p, a in zip(xgb_test_probs, iso_test_norm)
    ]
    decisions_test = [get_decision(s) for s in risk_scores_test]
    decision_counts = pd.Series(decisions_test).value_counts().to_dict()

    # 6. SHAP Explainability Engine
    print("\nInitializing SHAP TreeExplainer for real-time risk explanations...")
    explainer = shap.TreeExplainer(xgb_model)

    # 7. Serialize Artifacts
    models_dir = PROJECT_ROOT / "ml" / "saved_models"
    models_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(xgb_model, models_dir / "xgboost_model.joblib")
    joblib.dump(rf_model, models_dir / "random_forest.joblib")
    joblib.dump(lr_model, models_dir / "logistic_regression.joblib")
    joblib.dump(scaler, models_dir / "scaler.joblib")
    joblib.dump(iso_model, models_dir / "isolation_forest.joblib")
    joblib.dump(explainer, models_dir / "shap_explainer.joblib")
    joblib.dump(feature_names, models_dir / "feature_names.joblib")

    # Primary evaluated metrics payload (backward compatible with FastAPI schemas)
    top_eval = model_benchmarks["xgboost"]["test_metrics"]
    metrics_payload = {
        # Top-level fields expected by ModelMetricsResponse schema
        "precision": top_eval["precision"],
        "recall": top_eval["recall"],
        "f1_score": top_eval["f1_score"],
        "roc_auc": top_eval["roc_auc"],
        "confusion_matrix": top_eval["confusion_matrix"],
        "test_sample_count": top_eval["sample_count"],
        "fraud_count_test": top_eval["fraud_count"],
        "decision_distribution": decision_counts,
        # Enriched model comparison & validation metadata
        "pr_auc": top_eval["pr_auc"],
        "selected_threshold": top_eval["threshold"],
        "selected_model": "xgboost",
        "iso_normalization_bounds": {"min_val": iso_min, "max_val": iso_max},
        "chronological_splits": {
            "train": {
                "rows": len(X_train),
                "fraud_count": int(y_train.sum()),
                "fraud_rate_pct": round(float(y_train.mean() * 100), 2),
                "start_time": train_dates[0],
                "end_time": train_dates[1],
            },
            "validation": {
                "rows": len(X_val),
                "fraud_count": int(y_val.sum()),
                "fraud_rate_pct": round(float(y_val.mean() * 100), 2),
                "start_time": val_dates[0],
                "end_time": val_dates[1],
            },
            "test": {
                "rows": len(X_test),
                "fraud_count": int(y_test.sum()),
                "fraud_rate_pct": round(float(y_test.mean() * 100), 2),
                "start_time": test_dates[0],
                "end_time": test_dates[1],
            },
        },
        "model_benchmarks": model_benchmarks,
        "feature_columns": feature_names,
    }

    metrics_path = models_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\n[SUCCESS] Successfully serialized all models and metrics to: {models_dir}")
    print("=" * 70)

    return metrics_payload


if __name__ == "__main__":
    train_models()
