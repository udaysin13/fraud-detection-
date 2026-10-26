"""Investigation case creation, evidence and outcome-provenance tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.models.orm import CaseORM, TransactionORM
from backend.app.routes.entities import router


def test_case_workspace_preserves_prediction_label_separation():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(TransactionORM(
        transaction_id="TXN_WORKSPACE", timestamp="2026-10-12 10:00:00",
        sender_id="CUST_WORKSPACE", amount=500.0, amount_inr=500.0,
        risk_score=91.0, decision="Block", is_fraud=None,
    ))
    session.commit()
    session.close()
    app = FastAPI()
    app.include_router(router)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        created = client.post("/api/cases", json={"transaction_id": "TXN_WORKSPACE", "severity": "HIGH"}, headers={"X-Analyst": "Analyst A"})
        assert created.status_code == 201
        case_id = created.json()["case_id"]
        duplicate = client.post("/api/cases", json={"transaction_id": "TXN_WORKSPACE"})
        assert duplicate.status_code == 409
        assert client.post(f"/api/cases/{case_id}/notes", json={"note": "Reviewed device telemetry."}, headers={"X-Analyst": "Analyst A"}).status_code == 201
        updated = client.patch(f"/api/cases/{case_id}/status", json={"status": "Confirmed Fraud", "closure_reason": "Verified external evidence"}, headers={"X-Analyst": "Analyst A"})
        assert updated.status_code == 200
        assert updated.json()["outcome"] == "Confirmed Fraud"
        assert len(client.get(f"/api/cases/{case_id}/history").json()) >= 3

    session = factory()
    try:
        session.add(CaseORM(
            case_id="CASE_DUPLICATE_TXN",
            title="Duplicate transaction case",
            customer_id="CUST_WORKSPACE",
            transaction_id="TXN_WORKSPACE",
        ))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        transaction = session.query(TransactionORM).filter_by(transaction_id="TXN_WORKSPACE").one()
        assert transaction.is_fraud is None
    finally:
        session.close()
        engine.dispose()
