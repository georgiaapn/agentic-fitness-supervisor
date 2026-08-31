"""saved generated plans

Revision ID: 0004_saved_generated_plans
Revises: 0003_wearable_signals
Create Date: 2026-08-31
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_saved_generated_plans"
down_revision: str | None = "0003_wearable_signals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_generated_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("plan_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "plan_type", name="uq_saved_generated_plans_user_type"),
    )
    op.create_index("ix_saved_generated_plans_user_id", "saved_generated_plans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_generated_plans_user_id", table_name="saved_generated_plans")
    op.drop_table("saved_generated_plans")
