"""Operational alert lifecycle, history, and duplicate-suppression tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.routes.alerts import router


def test_alert_lifecycle_records_status_and_acknowledgement_history():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        created = client.post("/api/alerts", json={
            "alert_code": "ALT-LIFECYCLE-1", "title": "Rapid repeat activity",
            "segment": "UPI P2P", "time_ago": "Just now", "assignee": "Risk Engine",
            "severity": "HIGH",
        })
        assert created.status_code == 201
        alert_id = created.json()["id"]

        updated = client.patch(f"/api/alerts/{alert_id}", json={
            "status": "Investigating", "acknowledge": True,
        })
        assert updated.status_code == 200
        assert updated.json()["acknowledged_at"] is not None

        history = client.get(f"/api/alerts/{alert_id}/history")
        assert history.status_code == 200
        assert {event["event_type"] for event in history.json()} >= {"created", "status_changed", "acknowledged"}

        duplicate = client.post("/api/alerts", json={
            "alert_code": "ALT-LIFECYCLE-2", "title": "Rapid repeat activity",
            "segment": "UPI P2P", "time_ago": "Just now", "assignee": "Risk Engine",
        })
        assert duplicate.status_code == 409
    engine.dispose()
