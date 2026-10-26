"""Add severity, acknowledgement, and history to operational alerts.

Revision ID: 0003_alert_lifecycle
Revises: 0002_prediction_label_separation
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_alert_lifecycle"
down_revision = "0002_prediction_label_separation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("alerts")}
    if "severity" not in columns:
        op.add_column("alerts", sa.Column("severity", sa.String(length=255), nullable=True))
        op.execute("UPDATE alerts SET severity = 'MEDIUM' WHERE severity IS NULL")
    if "acknowledged_at" not in columns:
        op.add_column("alerts", sa.Column("acknowledged_at", sa.DateTime(), nullable=True))
    if "updated_at" not in columns:
        op.add_column("alerts", sa.Column("updated_at", sa.DateTime(), nullable=True))
    if "alert_history" not in inspector.get_table_names():
        op.create_table(
            "alert_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("alert_id", sa.Integer(), nullable=False, index=True),
            sa.Column("event_type", sa.String(length=255), nullable=False),
            sa.Column("previous_status", sa.String(length=255), nullable=True),
            sa.Column("new_status", sa.String(length=255), nullable=True),
            sa.Column("actor", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    raise RuntimeError(
        "Refusing to discard alert acknowledgement and history data. Restore a backup instead."
    )
