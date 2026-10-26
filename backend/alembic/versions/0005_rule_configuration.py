"""Add versioned, controlled risk-rule configuration.

Revision ID: 0005_rule_configuration
Revises: 0004_investigation_workspace
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_rule_configuration"
down_revision = "0004_investigation_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "rule_configs" not in tables:
        op.create_table(
            "rule_configs", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("rule_key", sa.String(length=255), nullable=False, unique=True, index=True),
            sa.Column("value", sa.Float(), nullable=False), sa.Column("enabled", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False), sa.Column("updated_by", sa.String(length=255), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "rule_history" not in tables:
        op.create_table(
            "rule_history", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("rule_key", sa.String(length=255), nullable=False, index=True),
            sa.Column("previous_value", sa.Float(), nullable=True), sa.Column("new_value", sa.Float(), nullable=False),
            sa.Column("previous_enabled", sa.Integer(), nullable=True), sa.Column("new_enabled", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False), sa.Column("changed_by", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    raise RuntimeError("Refusing to discard risk-rule configuration or its audit history automatically.")
