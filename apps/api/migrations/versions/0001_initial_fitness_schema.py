"""initial fitness schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-29
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(length=40), nullable=False),
        sa.Column("height_cm", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("fitness_level", sa.String(length=40), nullable=False),
        sa.Column("goal", sa.String(length=60), nullable=False),
        sa.Column("dietary_restrictions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("equipment_available", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("injury_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "daily_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=False),
        sa.Column("sleep_score", sa.Integer(), nullable=False),
        sa.Column("resting_heart_rate", sa.Integer(), nullable=False),
        sa.Column("stress_level", sa.Integer(), nullable=False),
        sa.Column("soreness_quads", sa.Integer(), nullable=False),
        sa.Column("soreness_upper", sa.Integer(), nullable=False),
        sa.Column("energy_level", sa.Integer(), nullable=False),
        sa.Column("pain_level", sa.Integer(), nullable=False),
        sa.Column("available_minutes", sa.Integer(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_checkins_user_id", "daily_checkins", ["user_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("check_in_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("recovery_status", sa.String(length=20), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False),
        sa.Column("selected_agents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("skipped_agents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("final_message", sa.Text(), nullable=False),
        sa.Column("response_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["check_in_id"], ["daily_checkins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_check_in_id", "agent_runs", ["check_in_id"])
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])

    op.create_table(
        "supervisor_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", sa.String(length=60), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supervisor_decisions_run_id", "supervisor_decisions", ["run_id"])

    op.create_table(
        "plan_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("plan_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_versions_run_id", "plan_versions", ["run_id"])
    op.create_index("ix_plan_versions_user_id", "plan_versions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_versions_user_id", table_name="plan_versions")
    op.drop_index("ix_plan_versions_run_id", table_name="plan_versions")
    op.drop_table("plan_versions")
    op.drop_index("ix_supervisor_decisions_run_id", table_name="supervisor_decisions")
    op.drop_table("supervisor_decisions")
    op.drop_index("ix_agent_runs_user_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_check_in_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_daily_checkins_user_id", table_name="daily_checkins")
    op.drop_table("daily_checkins")
    op.drop_table("user_profiles")
    op.drop_table("users")

