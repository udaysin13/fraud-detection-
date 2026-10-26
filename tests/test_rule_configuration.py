"""Authorization, versioning, and runtime rule-configuration tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.models.orm import RuleConfigORM
from backend.app.routes.rules import router
from backend.app.services.risk_rules import evaluate_transaction_rules, get_rule_configuration


def test_rule_updates_require_token_and_are_versioned(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setenv("VAULTGUARD_ADMIN_TOKEN", "test-token")
    with TestClient(app) as client:
        assert client.put("/api/rules/amount_review_threshold", json={"value": 2000, "enabled": True}).status_code == 401
        updated = client.put("/api/rules/amount_review_threshold", json={"value": 2000, "enabled": True}, headers={"X-Admin-Token": "test-token", "X-Analyst": "Admin A"})
        assert updated.status_code == 200
        assert updated.json()["version"] == 1
        assert client.get("/api/rules/amount_review_threshold/history").json()[0]["changed_by"] == "Admin A"
    db = factory()
    try:
        assert get_rule_configuration(db)["amount_review_threshold"] == 2000
        rule = db.query(RuleConfigORM).filter_by(rule_key="amount_review_threshold").one()
        rule.enabled = 0
        db.commit()
        monkeypatch.setenv("VAULTGUARD_AMOUNT_REVIEW_THRESHOLD", "1000")
        signals = evaluate_transaction_rules(
            {"timestamp": "2026-10-12 10:00:00", "amount_inr": 1500},
            db=db,
        )
        assert "amount_threshold" not in {signal["rule_id"] for signal in signals}
    finally:
        db.close()
        engine.dispose()


def test_rule_editing_fails_closed_without_configured_admin_token(monkeypatch):
    monkeypatch.delenv("VAULTGUARD_ADMIN_TOKEN", raising=False)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.put("/api/rules/amount_ratio_threshold", json={"value": 4, "enabled": True})
    assert response.status_code == 503
