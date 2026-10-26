"""Transparent, configurable rules that complement—never overwrite—ML scoring."""

import os
from typing import Any, Optional

import pandas as pd


def _int_setting(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except ValueError:
        return default


def _flag_setting(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError:
        return default
    return value if value in {0, 1} else default


def _float_setting(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, default)))
    except ValueError:
        return default


DEFAULT_RULE_CONFIGURATION = {
    "rapid_window_minutes": 10,
    "rapid_transaction_count": 3,
    "amount_ratio_threshold": 3.0,
    "amount_review_threshold": 50_000.0,
    "device_sim_change_enabled": 1,
    "unusual_time_enabled": 1,
    "new_beneficiary_enabled": 1,
}


def _load_rule_configuration(
    db: Any = None,
) -> tuple[dict[str, float | int], dict[str, bool]]:
    """Read environment defaults and persisted values and enabled states."""
    config: dict[str, float | int] = {
        "rapid_window_minutes": _int_setting("VAULTGUARD_RAPID_WINDOW_MINUTES", 10),
        "rapid_transaction_count": _int_setting("VAULTGUARD_RAPID_TRANSACTION_COUNT", 3),
        "amount_ratio_threshold": _float_setting("VAULTGUARD_AMOUNT_RATIO_THRESHOLD", 3.0),
        "amount_review_threshold": _float_setting("VAULTGUARD_AMOUNT_REVIEW_THRESHOLD", 50_000.0),
        "device_sim_change_enabled": _flag_setting("VAULTGUARD_DEVICE_SIM_CHANGE_ENABLED", 1),
        "unusual_time_enabled": _flag_setting("VAULTGUARD_UNUSUAL_TIME_ENABLED", 1),
        "new_beneficiary_enabled": _flag_setting("VAULTGUARD_NEW_BENEFICIARY_ENABLED", 1),
    }
    enabled = {key: True for key in config}
    if db is not None:
        from backend.app.models.orm import RuleConfigORM

        for rule in db.query(RuleConfigORM).all():
            if rule.rule_key in config:
                config[rule.rule_key] = rule.value
                enabled[rule.rule_key] = bool(rule.enabled)
    return config, enabled


def get_rule_configuration(db: Any = None) -> dict[str, float | int]:
    """Return effective values from environment defaults and persisted overrides."""
    return _load_rule_configuration(db)[0]


def evaluate_transaction_rules(
    transaction: dict[str, Any], history_df: Optional[pd.DataFrame] = None, db: Any = None
) -> list[dict[str, str]]:
    """Evaluate only signals available in transaction data and prior sender history."""
    config, enabled = _load_rule_configuration(db)
    signals: list[dict[str, str]] = []
    amount = float(transaction.get("amount_inr") or transaction.get("amount") or 0.0)
    timestamp = pd.to_datetime(transaction.get("timestamp"), errors="coerce")

    def add(rule_id: str, severity: str, message: str) -> None:
        signals.append({"rule_id": rule_id, "severity": severity, "message": message})

    new_device = int(transaction.get("is_new_device") or 0) == 1
    sim_changed = int(transaction.get("sim_change_flag") or 0) == 1
    if enabled["device_sim_change_enabled"]:
        if config["device_sim_change_enabled"] and new_device and sim_changed:
            add("device_sim_change", "high", "New device and recent SIM change were both reported.")
        elif new_device:
            add("new_device", "review", "Transaction originated from a device marked as new.")
        elif sim_changed:
            add("sim_change", "review", "A recent SIM change was reported for the sender.")

    if (
        enabled["amount_review_threshold"]
        and config["amount_review_threshold"]
        and amount >= config["amount_review_threshold"]
    ):
        add("amount_threshold", "review", "Amount exceeds the configured review threshold.")
    if (
        enabled["unusual_time_enabled"]
        and config["unusual_time_enabled"]
        and not pd.isna(timestamp)
        and timestamp.hour in {23, 0, 1, 2, 3, 4, 5}
    ):
        add("unusual_time", "info", "Transaction occurred during the configured overnight window.")

    if history_df is None or history_df.empty:
        return signals
    history = history_df.copy()
    # Defend the rule engine itself against accidentally supplied future context.
    # Database callers already enforce this, but rules must remain point-in-time safe
    # when used by CSV analysis or tests.
    if not pd.isna(timestamp) and "timestamp" in history:
        historical_timestamps = pd.to_datetime(history["timestamp"], errors="coerce")
        history = history.loc[historical_timestamps < timestamp].copy()
    if history.empty:
        return signals
    historical_amounts = pd.to_numeric(history.get("amount_inr", history.get("amount")), errors="coerce").dropna()
    if (
        enabled["amount_ratio_threshold"]
        and config["amount_ratio_threshold"] > 0
        and not historical_amounts.empty
        and historical_amounts.mean() > 0
    ):
        if amount / historical_amounts.mean() >= config["amount_ratio_threshold"]:
            add("amount_anomaly", "review", "Amount is elevated relative to the sender's prior average.")

    beneficiary = transaction.get("beneficiary_id") or transaction.get("merchant_id")
    if (
        enabled["new_beneficiary_enabled"]
        and config["new_beneficiary_enabled"]
        and beneficiary
        and "beneficiary_id" in history
        and beneficiary not in set(history["beneficiary_id"].dropna().astype(str))
    ):
        add("new_beneficiary", "review", "Beneficiary does not appear in the available prior sender history.")

    if (
        enabled["rapid_window_minutes"]
        and enabled["rapid_transaction_count"]
        and not pd.isna(timestamp)
        and "timestamp" in history
    ):
        historical_times = pd.to_datetime(history["timestamp"], errors="coerce").dropna()
        cutoff = timestamp - pd.Timedelta(minutes=config["rapid_window_minutes"])
        recent_count = int(((historical_times >= cutoff) & (historical_times < timestamp)).sum())
        if recent_count >= config["rapid_transaction_count"]:
            add("rapid_repeat", "review", "Prior transactions exceed the configured rapid-repeat threshold.")
    return signals


def recommended_action(risk_category: str, rule_signals: list[dict[str, str]]) -> str:
    """Return an analyst recommendation; VaultGuard never blocks a real payment."""
    if risk_category == "HIGH_RISK" or any(item["severity"] == "high" for item in rule_signals):
        return "Review Required"
    if risk_category == "REVIEW" or any(item["severity"] == "review" for item in rule_signals):
        return "Manual Review Recommended"
    return "No Additional Review Recommended"
