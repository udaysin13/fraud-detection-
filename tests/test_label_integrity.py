"""Regression tests that keep model predictions separate from verified labels."""

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.models.orm import TransactionORM
from backend.app.routes import transactions
from ml.predict import normalize_iso_score
from ml.train import get_verified_training_labels


def test_prediction_does_not_create_a_confirmed_fraud_label(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autoflush=False, bind=engine)
    app = FastAPI()
    app.include_router(transactions.router)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        transactions,
        "predict_single_transaction",
        lambda *_args, **_kwargs: {
            "transaction_id": "TXN_PREDICTION_ONLY",
            "risk_score": 95.0,
            "decision": "Block",
            "risk_category": "HIGH_RISK",
            "reasons": ["Test signal"],
            "xgb_probability": 0.99,
            "anomaly_score": 0.8,
            "fraud_probability": 0.99,
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/predict",
            json={
                "transaction_id": "TXN_PREDICTION_ONLY",
                "amount_inr": 5000.0,
                "sender_id": "CUST_LABEL_TEST",
            },
        )
    assert response.status_code == 200

    session = session_factory()
    try:
        saved = session.query(TransactionORM).filter_by(
            transaction_id="TXN_PREDICTION_ONLY"
        ).one()
        assert saved.decision == "Block"
        assert saved.risk_score == 95.0
        assert saved.is_fraud is None
        assert saved.label_source is None
        assert saved.label_confirmed_at is None
        assert saved.status == "Review Required"
    finally:
        session.close()
        engine.dispose()


def test_training_rejects_prediction_derived_label_sources():
    rows = pd.DataFrame(
        {
            "is_fraud": [0, 1],
            "label_source": ["model_prediction", "model_prediction"],
            "fraud_probability": [0.1, 0.9],
        }
    )
    try:
        get_verified_training_labels(rows)
    except ValueError as exc:
        assert "model predictions" in str(exc)
    else:
        raise AssertionError("prediction-derived labels must not be used for training")


def test_isolation_forest_normalization_uses_persisted_training_bounds():
    metrics = {"iso_normalization_bounds": {"min_val": -0.2, "max_val": 0.2}}
    raw_score = -0.1
    expected = normalize_iso_score(raw_score, metrics)
    assert expected == normalize_iso_score(raw_score, metrics)
    assert expected == pytest.approx(0.75)
