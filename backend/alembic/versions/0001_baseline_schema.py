"""Create the VaultGuard baseline schema for a new database.

Revision ID: 0001_baseline_schema
Revises:
Create Date: 2026-10-20
"""

from alembic import op

from backend.app.database import Base
import backend.app.models.orm  # noqa: F401 -- registers the complete schema


revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the baseline schema only for an explicitly upgraded new database."""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Refuse implicit table deletion; restore from backup or use a new database instead."""
    raise RuntimeError(
        "VaultGuard does not provide a destructive baseline downgrade. "
        "Restore a backup or create a new development database instead."
    )
