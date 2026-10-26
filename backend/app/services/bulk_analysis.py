"""Validated, in-memory CSV analysis using VaultGuard's persisted ML artifacts."""

import csv
import io
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from ml.features import engineer_features
from ml.predict import derive_reasons, get_decision, get_risk_category, load_models, normalize_iso_score
from backend.app.services.risk_rules import evaluate_transaction_rules, recommended_action

MAX_UPLOAD_BYTES = int(os.getenv("BULK_ANALYSIS_MAX_BYTES", 5 * 1024 * 1024))
MAX_ROWS = int(os.getenv("BULK_ANALYSIS_MAX_ROWS", 10_000))
RESULT_TTL_SECONDS = int(os.getenv("BULK_ANALYSIS_RESULT_TTL_SECONDS", 60 * 60))

REQUIRED_COLUMNS = ("transaction_id", "timestamp", "amount_inr", "sender_id")
OPTIONAL_COLUMNS = (
    "beneficiary_id", "merchant_id", "channel", "transaction_type", "merchant_category",
    "device_id", "is_new_device", "sim_change_flag", "sender_vpa", "beneficiary_vpa",
    "ip_location_state", "country", "billing_country", "bin_range", "is_fraud",
)
SUPPORTED_CHANNELS = {"UPI_P2P", "UPI_P2M_QR", "WALLET", "IMPS", "RUPAY_CARD"}
SUPPORTED_TRANSACTION_TYPES = {"QR_PAYMENT", "P2P_TRANSFER", "MERCHANT_PAYMENT", "COLLECT_REQUEST"}
SUPPORTED_MERCHANT_CATEGORIES = {
    "food_dining", "kirana_grocery", "digital_services", "transport_travel",
    "retail_fashion", "pharmacy_health", "electronics", "gaming_entertainment", "p2p_transfer",
}

_RESULTS: dict[str, dict[str, Any]] = {}


def accepted_schema() -> dict[str, Any]:
    return {
        "required_columns": list(REQUIRED_COLUMNS),
        "optional_columns": list(OPTIONAL_COLUMNS),
        "max_rows": MAX_ROWS,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
    }


def sample_csv_bytes() -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS[:10]])
    writer.writeheader()
    writer.writerow({
        "transaction_id": "UPLOAD_TXN_001", "timestamp": "2026-10-12 10:30:00",
        "amount_inr": "185.50", "sender_id": "CUST_UPLOAD_001", "beneficiary_id": "MERCH_UPLOAD_01",
        "merchant_id": "MERCH_UPLOAD_01", "channel": "UPI_P2M_QR",
        "transaction_type": "MERCHANT_PAYMENT", "merchant_category": "kirana_grocery",
        "device_id": "DEV_UPLOAD_01", "is_new_device": "0", "sim_change_flag": "0",
    })
    return output.getvalue().encode("utf-8")


def _parse_flag(value: str, name: str) -> int:
    if value in ("", None):
        return 0
    if str(value).strip() not in {"0", "1"}:
        raise ValueError(f"{name} must be 0 or 1")
    return int(value)


def _parse_optional_label(value: str | None) -> int | None:
    """Preserve a user-supplied binary label without granting it verified status."""
    if value in ("", None):
        return None
    if str(value).strip() not in {"0", "1"}:
        raise ValueError("is_fraud, when supplied, must be 0 or 1")
    return int(value)


def _validate_row(row: dict[str, str], seen_ids: set[str]) -> tuple[dict[str, Any], str | None]:
    if None in row:
        return row, "row contains more values than the CSV header defines"
    clean = {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
    transaction_id = clean.get("transaction_id", "")
    if not transaction_id:
        return clean, "transaction_id is required"
    if transaction_id in seen_ids:
        return clean, "duplicate transaction_id in uploaded file"
    seen_ids.add(transaction_id)
    if not clean.get("sender_id"):
        return clean, "sender_id is required"
    try:
        amount = float(clean.get("amount_inr", ""))
        if not np.isfinite(amount) or amount < 0 or amount > 10_000_000:
            raise ValueError
    except (TypeError, ValueError):
        return clean, "amount_inr must be a number from 0 to 10000000"
    timestamp = pd.to_datetime(clean.get("timestamp", ""), errors="coerce")
    if pd.isna(timestamp):
        return clean, "timestamp must be a valid date/time"
    channel = clean.get("channel") or "UPI_P2P"
    if channel not in SUPPORTED_CHANNELS:
        return clean, f"unsupported channel: {channel}"
    transaction_type = clean.get("transaction_type") or "P2P_TRANSFER"
    if transaction_type not in SUPPORTED_TRANSACTION_TYPES:
        return clean, f"unsupported transaction_type: {transaction_type}"
    merchant_category = clean.get("merchant_category") or "p2p_transfer"
    if merchant_category not in SUPPORTED_MERCHANT_CATEGORIES:
        return clean, f"unsupported merchant_category: {merchant_category}"
    try:
        clean["is_new_device"] = _parse_flag(clean.get("is_new_device"), "is_new_device")
        clean["sim_change_flag"] = _parse_flag(clean.get("sim_change_flag"), "sim_change_flag")
        clean["is_fraud"] = _parse_optional_label(clean.get("is_fraud"))
    except ValueError as exc:
        return clean, str(exc)
    clean.update({
        "amount_inr": amount,
        "amount": amount,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "channel": channel,
        "transaction_type": transaction_type,
        "merchant_category": merchant_category,
        "merchant_id": clean.get("merchant_id") or "NOT_APPLICABLE",
        "beneficiary_id": clean.get("beneficiary_id") or clean.get("merchant_id") or "",
    })
    return clean, None


def _prune_expired_results() -> None:
    cutoff = time.time() - RESULT_TTL_SECONDS
    for key in [key for key, value in _RESULTS.items() if value["created_at"] < cutoff]:
        _RESULTS.pop(key, None)


def analyse_csv(content: bytes, db: Any = None) -> dict[str, Any]:
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds the {MAX_UPLOAD_BYTES} byte upload limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 or UTF-8 with BOM encoded.") from exc

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        headers = reader.fieldnames or []
        if not headers:
            raise ValueError("CSV is missing a header row.")
        if any(not header or not header.strip() for header in headers):
            raise ValueError("CSV headers must be non-empty.")
        if len(set(headers)) != len(headers):
            raise ValueError("CSV contains duplicate header names.")
        missing = [name for name in REQUIRED_COLUMNS if name not in headers]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        rows = list(reader)
    except csv.Error as exc:
        raise ValueError("CSV is malformed or has invalid quoting.") from exc
    if not rows:
        raise ValueError("CSV contains no transaction rows.")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"CSV exceeds the {MAX_ROWS} row limit.")

    extras = [name for name in headers if name not in {*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS}]
    records: list[dict[str, Any]] = []
    valid_inputs: list[dict[str, Any]] = []
    valid_positions: list[int] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        original = dict(row)
        clean, error = _validate_row(original, seen_ids)
        record = {
            "source_row": row_number,
            "original": original,
            "transaction_id": clean.get("transaction_id", ""),
            "validation_status": "valid" if error is None else "invalid",
            "error_reason": error,
        }
        records.append(record)
        if error is None:
            valid_positions.append(len(records) - 1)
            valid_inputs.append(clean)

    if valid_inputs:
        try:
            models = load_models()
            frame = pd.DataFrame(valid_inputs)
            features, _ = engineer_features(frame)
            names = models["feature_names"]
            matrix = features[names]
            xgb_probabilities = models["xgb_model"].predict_proba(matrix)[:, 1]
            iso_raw_scores = models["iso_model"].decision_function(matrix)
            metrics = models.get("metrics", {})
            anomaly_scores = [normalize_iso_score(float(raw), metrics) for raw in iso_raw_scores]
            shap_values = models["explainer"].shap_values(matrix)
        except FileNotFoundError:
            raise
        except Exception as exc:
            raise RuntimeError("Bulk inference failed; no results were persisted.") from exc

        for index, position in enumerate(valid_positions):
            probability = float(xgb_probabilities[index])
            anomaly = float(anomaly_scores[index])
            score = round(float(np.clip((0.75 * probability + 0.25 * anomaly) * 100, 0, 100)), 1)
            rule_signals = evaluate_transaction_rules(valid_inputs[index], db=db)
            records[position].update({
                "predicted_class": "Suspected Fraud" if score > 40 else "Normal Prediction",
                "fraud_probability": round(probability, 4),
                "risk_score": score,
                "risk_category": get_risk_category(score),
                "recommended_action": recommended_action(get_risk_category(score), rule_signals),
                "reasons": derive_reasons(matrix.iloc[index], shap_values[index], names),
                "rule_signals": rule_signals,
                # User labels are retained separately and never treated as verified
                # evidence or passed to the inference feature matrix.
                "ground_truth_label": valid_inputs[index].get("is_fraud"),
                "ground_truth_status": "unverified_user_supplied"
                if valid_inputs[index].get("is_fraud") is not None else None,
            })

    valid_records = [record for record in records if record["validation_status"] == "valid"]
    suspected = sum(record.get("predicted_class") == "Suspected Fraud" for record in valid_records)
    high_risk = sum(record.get("risk_category") == "HIGH_RISK" for record in valid_records)
    scores = [record["risk_score"] for record in valid_records]
    _prune_expired_results()
    result_id = uuid.uuid4().hex
    result = {
        "analysis_id": result_id,
        "created_at": time.time(),
        "schema": accepted_schema(),
        "extra_columns": extras,
        "summary": {
            "total_rows": len(rows), "analysed_rows": len(valid_records), "invalid_rows": len(rows) - len(valid_records),
            "suspected_fraud": suspected, "normal_predictions": len(valid_records) - suspected,
            "high_risk": high_risk, "average_risk_score": round(float(np.mean(scores)), 2) if scores else None,
        },
        "records": records,
    }
    _RESULTS[result_id] = result
    return {key: value for key, value in result.items() if key != "created_at"}


def get_result(analysis_id: str) -> dict[str, Any] | None:
    _prune_expired_results()
    result = _RESULTS.get(analysis_id)
    if result is None:
        return None
    return {key: value for key, value in result.items() if key != "created_at"}


def sanitize_csv_cell(value: Any) -> Any:
    if value is None:
        return ""
    value = str(value)
    return "'" + value if value[:1] in {"=", "+", "-", "@", "\t", "\r"} else value


def result_csv(analysis_id: str) -> str | None:
    result = get_result(analysis_id)
    if result is None:
        return None
    original_headers = list(result["records"][0]["original"].keys()) if result["records"] else []
    fieldnames = original_headers + [
        "source_row", "transaction_id", "predicted_class", "fraud_probability", "risk_score",
        "risk_category", "recommended_action", "validation_status", "error_reason", "reasons", "rule_signals",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in result["records"]:
        row = {key: sanitize_csv_cell(value) for key, value in record["original"].items()}
        row.update({
            key: sanitize_csv_cell(
                value if key != "reasons" else "; ".join(value or [])
            )
            for key, value in record.items() if key not in {"original", "ground_truth_label"}
        })
        writer.writerow(row)
    return output.getvalue()
