"""Tests for transparent risk-rule signals and recommendations."""

import pandas as pd

from backend.app.services.risk_rules import evaluate_transaction_rules, recommended_action


def test_rules_use_prior_history_and_keep_a_separate_recommendation(monkeypatch):
    monkeypatch.setenv("VAULTGUARD_RAPID_WINDOW_MINUTES", "10")
    monkeypatch.setenv("VAULTGUARD_RAPID_TRANSACTION_COUNT", "2")
    history = pd.DataFrame([
        {"timestamp": "2026-10-12 10:01:00", "amount_inr": 100.0, "beneficiary_id": "KNOWN"},
        {"timestamp": "2026-10-12 10:05:00", "amount_inr": 100.0, "beneficiary_id": "KNOWN"},
    ])
    signals = evaluate_transaction_rules({
        "timestamp": "2026-10-12 10:08:00", "amount_inr": 500.0,
        "beneficiary_id": "NEW", "is_new_device": 1, "sim_change_flag": 1,
    }, history)
    ids = {signal["rule_id"] for signal in signals}
    assert {"device_sim_change", "amount_anomaly", "new_beneficiary", "rapid_repeat"} <= ids
    assert recommended_action("LOW_RISK", signals) == "Review Required"


def test_low_risk_without_signals_does_not_claim_a_payment_action():
    assert recommended_action("LOW_RISK", []) == "No Additional Review Recommended"


def test_future_history_cannot_create_a_rule_signal():
    history = pd.DataFrame([
        {"timestamp": "2026-10-12 10:10:00", "amount_inr": 1.0, "beneficiary_id": "FUTURE_ONLY"},
    ])
    signals = evaluate_transaction_rules({
        "timestamp": "2026-10-12 10:00:00", "amount_inr": 100.0,
        "beneficiary_id": "FUTURE_ONLY",
    }, history)
    ids = {signal["rule_id"] for signal in signals}
    assert "amount_anomaly" not in ids
    assert "new_beneficiary" not in ids


def test_environment_zero_disables_binary_rule_signals(monkeypatch):
    monkeypatch.setenv("VAULTGUARD_DEVICE_SIM_CHANGE_ENABLED", "0")
    signals = evaluate_transaction_rules({
        "timestamp": "2026-10-12 10:00:00",
        "amount_inr": 100,
        "is_new_device": 1,
        "sim_change_flag": 1,
    })
    rule_ids = {signal["rule_id"] for signal in signals}
    assert "device_sim_change" not in rule_ids
    assert "new_device" in rule_ids
