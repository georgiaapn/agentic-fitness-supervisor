"""add wearable signal columns

Revision ID: 0003_wearable_signals
Revises: 0002_knowledge_base
Create Date: 2026-08-30
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_wearable_signals"
down_revision: str | None = "0002_knowledge_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "daily_checkins",
        sa.Column("blood_oxygen_level", sa.Float(), nullable=False, server_default="98"),
    )
    op.add_column(
        "daily_checkins",
        sa.Column("step_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "daily_checkins",
        sa.Column(
            "activity_level",
            sa.String(length=40),
            nullable=False,
            server_default="moderately_active",
        ),
    )
    op.alter_column("daily_checkins", "blood_oxygen_level", server_default=None)
    op.alter_column("daily_checkins", "step_count", server_default=None)
    op.alter_column("daily_checkins", "activity_level", server_default=None)


def downgrade() -> None:
    op.drop_column("daily_checkins", "activity_level")
    op.drop_column("daily_checkins", "step_count")
    op.drop_column("daily_checkins", "blood_oxygen_level")
