"""Bulk CSV analysis validation and export regression tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models.orm import RuleConfigORM
from backend.app.routes.bulk_analysis import router
from backend.app.services.bulk_analysis import analyse_csv, result_csv


VALID_HEADER = "transaction_id,timestamp,amount_inr,sender_id,channel,transaction_type,merchant_category\n"
VALID_ROW = "BULK_TEST_1,2026-10-12 10:00:00,125.50,CUST_BULK,UPI_P2P,P2P_TRANSFER,p2p_transfer\n"


def test_valid_csv_uses_model_and_returns_separate_prediction_fields():
    result = analyse_csv((VALID_HEADER + VALID_ROW).encode())
    row = result["records"][0]
    assert result["summary"]["analysed_rows"] == 1
    assert row["validation_status"] == "valid"
    assert row["predicted_class"] in {"Normal Prediction", "Suspected Fraud"}
    assert 0 <= row["fraud_probability"] <= 1
    assert 0 <= row["risk_score"] <= 100
    assert "is_fraud" not in row


def test_bulk_analysis_uses_persisted_rule_configuration():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    try:
        db.add(RuleConfigORM(
            rule_key="amount_review_threshold",
            value=100,
            enabled=1,
            version=1,
            updated_by="test",
        ))
        db.commit()
        row = analyse_csv((VALID_HEADER + VALID_ROW).encode(), db=db)["records"][0]
        assert "amount_threshold" in {signal["rule_id"] for signal in row["rule_signals"]}
    finally:
        db.close()
        engine.dispose()


def test_missing_required_columns_are_rejected():
    with pytest.raises(ValueError, match="Missing required columns"):
        analyse_csv(b"transaction_id,amount_inr\nX,15\n")


def test_invalid_rows_and_duplicate_ids_are_reported_without_becoming_predictions():
    content = (
        VALID_HEADER
        + VALID_ROW
        + "BULK_TEST_1,not-a-time,invalid,CUST_BULK,UPI_P2P,P2P_TRANSFER,p2p_transfer\n"
    ).encode()
    result = analyse_csv(content)
    assert result["summary"]["analysed_rows"] == 1
    assert result["summary"]["invalid_rows"] == 1
    assert result["records"][1]["validation_status"] == "invalid"
    assert "predicted_class" not in result["records"][1]


def test_optional_user_label_is_preserved_but_not_treated_as_verified():
    content = (
        VALID_HEADER.replace("merchant_category\n", "merchant_category,is_fraud\n")
        + VALID_ROW.replace("p2p_transfer\n", "p2p_transfer,0\n")
    ).encode()
    row = analyse_csv(content)["records"][0]
    assert row["ground_truth_label"] == 0
    assert row["ground_truth_status"] == "unverified_user_supplied"


def test_duplicate_headers_and_extra_values_are_not_silently_accepted():
    with pytest.raises(ValueError, match="duplicate header"):
        analyse_csv(b"transaction_id,transaction_id,timestamp,amount_inr,sender_id\nA,B,2026-10-12,1,C\n")

    result = analyse_csv((VALID_HEADER + VALID_ROW.rstrip() + ",unexpected\n").encode())
    assert result["records"][0]["validation_status"] == "invalid"
    assert "more values" in result["records"][0]["error_reason"]


def test_export_neutralizes_formula_cells():
    content = (
        VALID_HEADER
        + "=FORMULA,2026-10-12 10:00:00,125.50,CUST_BULK,UPI_P2P,P2P_TRANSFER,p2p_transfer\n"
    ).encode()
    result = analyse_csv(content)
    exported = result_csv(result["analysis_id"])
    assert "'=FORMULA" in exported


def test_upload_endpoint_returns_validation_error_for_empty_csv():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post(
            "/api/bulk-analysis/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()
