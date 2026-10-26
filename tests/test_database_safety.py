"""Regression tests for non-destructive database initialization."""

import pytest

from backend.app import database
from backend.app.services import data_loader


def test_schema_validation_failure_never_drops_existing_tables(monkeypatch):
    """A failed schema query must stop startup without calling drop_all."""
    class FailingQuery:
        def count(self):
            raise RuntimeError("missing column")

    class FailingSession:
        def query(self, *_args, **_kwargs):
            return FailingQuery()

        def close(self):
            pass

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("drop_all must never run during normal startup")

    monkeypatch.setattr(data_loader, "verify_database_connection", lambda: None)
    monkeypatch.setattr(data_loader.Base.metadata, "create_all", lambda **_kwargs: None)
    monkeypatch.setattr(data_loader.Base.metadata, "drop_all", fail_if_called)
    monkeypatch.setattr(data_loader, "SessionLocal", lambda: FailingSession())

    with pytest.raises(RuntimeError, match="Existing data was left unchanged"):
        data_loader.seed_database_on_first_run()


def test_development_reset_requires_environment_and_exact_confirmation(monkeypatch):
    """The destructive helper is unavailable by default and fails before any write."""
    monkeypatch.delenv("VAULTGUARD_ENV", raising=False)
    with pytest.raises(RuntimeError, match="development"):
        data_loader.reset_development_database("DELETE ALL VAULTGUARD DATA")

    monkeypatch.setenv("VAULTGUARD_ENV", "development")
    with pytest.raises(RuntimeError, match="confirmation"):
        data_loader.reset_development_database("no")


def test_safe_database_url_masks_passwords():
    safe = database.safe_database_url(
        "mysql+pymysql://analyst:p%40ss%3Aword@localhost:3306/vaultguard_db"
    )
    assert "p%40ss" not in safe
    assert safe == "mysql+pymysql://analyst:***@localhost:3306/vaultguard_db"
