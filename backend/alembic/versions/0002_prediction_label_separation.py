"""Add provenance fields for verified transaction labels.

Revision ID: 0002_prediction_label_separation
Revises: 0001_baseline_schema
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_prediction_label_separation"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Preserve existing rows while adding provenance and nullable labels."""
    bind = op.get_bind()
    columns = {
        column["name"]: column
        for column in sa.inspect(bind).get_columns("transactions")
    }
    if "label_source" not in columns:
        op.add_column("transactions", sa.Column("label_source", sa.String(length=255), nullable=True))
    if "label_confirmed_at" not in columns:
        op.add_column("transactions", sa.Column("label_confirmed_at", sa.DateTime(), nullable=True))

    # SQLite needs Alembic's controlled copy-and-swap to relax a NOT NULL
    # constraint. This is an explicit, row-preserving migration—not startup repair.
    if not columns.get("is_fraud", {}).get("nullable", True):
        with op.batch_alter_table("transactions", recreate="always") as batch_op:
            batch_op.alter_column(
                "is_fraud",
                existing_type=sa.Integer(),
                existing_nullable=False,
                nullable=True,
            )


def downgrade() -> None:
    raise RuntimeError(
        "Refusing to remove label-provenance columns automatically. "
        "Restore a verified backup if a rollback is required."
    )
