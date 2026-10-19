from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.models.orm import CaseORM, FraudAlertORM, TransactionORM
from backend.app.routes.entities import router as entities_router


def build_test_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app = FastAPI()
    app.include_router(entities_router)

    def override_get_db():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), test_session, engine


def test_case_queue_and_status_actions_commit_and_filter_terminal_items():
    client, test_session, engine = build_test_client()
    session = test_session()
    try:
        session.add(
            TransactionORM(
                transaction_id="TXN_CASE_ACTION_TEST",
                timestamp="2026-10-19 12:00:00",
                amount=725.0,
                amount_inr=725.0,
                channel="UPI_P2P",
                decision="Block",
            )
        )
        session.add(
            CaseORM(
                case_id="CASE_ACTION_TEST",
                title="Analyst action test",
                customer_id="CUST_ACTION_TEST",
                risk_score=88.0,
                status="Open",
                assigned_analyst="Unassigned",
            )
        )
        session.add(
            FraudAlertORM(
                alert_id="FA-ACTION-TEST",
                transaction_id="TXN_CASE_ACTION_TEST",
                risk_score=88.0,
                risk_category="HIGH_RISK",
                reasons='["New device signal"]',
                review_status="OPEN",
            )
        )
        session.commit()

        queue_response = client.get("/api/cases/active")
        assert queue_response.status_code == 200
        queue = queue_response.json()
        assert queue["cases"][0]["case_id"] == "CASE_ACTION_TEST"
        alert = next(item for item in queue["alerts"] if item["alert_id"] == "FA-ACTION-TEST")
        assert alert["transaction_id"] == "TXN_CASE_ACTION_TEST"
        assert alert["amount_inr"] == 725.0
        assert alert["reasons"] == ["New device signal"]

        case_update = client.patch(
            "/api/cases/CASE_ACTION_TEST/status",
            json={"status": "False Positive"},
        )
        assert case_update.status_code == 200
        assert case_update.json()["status"] == "False Positive"

        alert_update = client.patch(
            f"/api/fraud-alerts/{alert['id']}/status",
            json={"status": "Under Review"},
        )
        assert alert_update.status_code == 200
        assert alert_update.json()["status"] == "UNDER_REVIEW"

        confirmed = client.patch(
            f"/api/fraud-alerts/{alert['id']}/status",
            json={"status": "Confirmed Fraud"},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "CONFIRMED_FRAUD"

        refreshed_queue = client.get("/api/cases/active").json()
        assert all(item["case_id"] != "CASE_ACTION_TEST" for item in refreshed_queue["cases"])
        assert all(item["alert_id"] != "FA-ACTION-TEST" for item in refreshed_queue["alerts"])

        invalid_status = client.patch(
            "/api/cases/CASE_ACTION_TEST/status",
            json={"status": "Definitely Fraud"},
        )
        assert invalid_status.status_code == 422
    finally:
        session.close()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_case_status_update_rolls_back_database_errors():
    client, test_session, engine = build_test_client()
    session = test_session()
    session.add(
        CaseORM(
            case_id="CASE_ROLLBACK_TEST",
            title="Rollback test",
            customer_id="CUST_ROLLBACK_TEST",
            risk_score=72.0,
            status="Open",
            assigned_analyst="Unassigned",
        )
    )
    session.commit()
    session.close()

    delegated_session = test_session()

    class FailingSession:
        def query(self, *args, **kwargs):
            return delegated_session.query(*args, **kwargs)

        def commit(self):
            raise SQLAlchemyError("simulated database write failure")

        def rollback(self):
            self.rolled_back = True
            delegated_session.rollback()

        def refresh(self, _record):
            raise AssertionError("refresh must not run after a failed commit")

    failing_session = FailingSession()

    def override_get_db():
        yield failing_session

    client.app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.patch(
            "/api/cases/CASE_ROLLBACK_TEST/status",
            json={"status": "Escalated"},
        )
        assert response.status_code == 500
        assert failing_session.rolled_back is True
    finally:
        delegated_session.close()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()