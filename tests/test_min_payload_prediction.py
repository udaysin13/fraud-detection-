"""Test minimal payload prediction does not raise KeyError and returns expected fields."""
import json
from backend.main import run_real_prediction

def test_min_payload_prediction():
    payload = {"amount_inr": 50000, "channel": "UPI_P2P"}
    result = run_real_prediction(payload)
    # Result should be a dict with expected keys
    expected_keys = {"risk_score", "decision", "risk_category", "fraud_probability", "anomaly_score"}
    assert isinstance(result, dict)
    assert expected_keys.issubset(result.keys())
    # Ensure numeric types for scores
    assert isinstance(result["risk_score"], (int, float))
    assert isinstance(result["fraud_probability"], (int, float))
    assert isinstance(result["anomaly_score"], (int, float))

