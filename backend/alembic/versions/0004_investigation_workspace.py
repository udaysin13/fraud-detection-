"""Add investigation case evidence and audit history.

Revision ID: 0004_investigation_workspace
Revises: 0003_alert_lifecycle
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_investigation_workspace"
down_revision = "0003_alert_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    case_columns = {column["name"] for column in inspector.get_columns("cases")}
    case_indexes = {index["name"] for index in inspector.get_indexes("cases")}
    for name, column in (
        ("transaction_id", sa.Column("transaction_id", sa.String(length=255), nullable=True)),
        ("severity", sa.Column("severity", sa.String(length=255), nullable=True)),
        ("outcome", sa.Column("outcome", sa.String(length=255), nullable=True)),
        ("closure_reason", sa.Column("closure_reason", sa.Text(), nullable=True)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(), nullable=True)),
    ):
        if name not in case_columns:
            op.add_column("cases", column)
    if "uq_cases_transaction_id" not in case_indexes:
        op.create_index(
            "uq_cases_transaction_id",
            "cases",
            ["transaction_id"],
            unique=True,
        )
    if "case_notes" not in inspector.get_table_names():
        op.create_table(
            "case_notes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("case_id", sa.String(length=255), nullable=False, index=True),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("author", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "case_history" not in inspector.get_table_names():
        op.create_table(
            "case_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("case_id", sa.String(length=255), nullable=False, index=True),
            sa.Column("event_type", sa.String(length=255), nullable=False),
            sa.Column("previous_status", sa.String(length=255), nullable=True),
            sa.Column("new_status", sa.String(length=255), nullable=True),
            sa.Column("actor", sa.String(length=255), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    raise RuntimeError("Refusing to discard investigation notes or audit history automatically.")
