"""saved daily adjustments

Revision ID: 0005_saved_daily_adjustments
Revises: 0004_saved_generated_plans
Create Date: 2026-08-31
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_saved_daily_adjustments"
down_revision: str | None = "0004_saved_generated_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_daily_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("adjustment_date", sa.Date(), nullable=False),
        sa.Column("current_day", sa.String(length=20), nullable=False),
        sa.Column("recovery_status", sa.String(length=20), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "adjustment_date", name="uq_saved_daily_adjustments_user_date"),
    )
    op.create_index("ix_saved_daily_adjustments_user_id", "saved_daily_adjustments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_daily_adjustments_user_id", table_name="saved_daily_adjustments")
    op.drop_table("saved_daily_adjustments")
