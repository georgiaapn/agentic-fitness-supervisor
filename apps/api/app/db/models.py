from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    profile: Mapped["UserProfileRecord"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    check_ins: Mapped[list["DailyCheckIn"]] = relationship(back_populates="user")
    runs: Mapped[list["AgentRun"]] = relationship(back_populates="user")


class UserProfileRecord(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(40), nullable=False)
    height_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    fitness_level: Mapped[str] = mapped_column(String(40), nullable=False)
    goal: Mapped[str] = mapped_column(String(60), nullable=False)
    dietary_restrictions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    equipment_available: Mapped[dict] = mapped_column(JSONB, nullable=False)
    injury_history: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="profile")


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    sleep_score: Mapped[int] = mapped_column(Integer, nullable=False)
    resting_heart_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    stress_level: Mapped[int] = mapped_column(Integer, nullable=False)
    soreness_quads: Mapped[int] = mapped_column(Integer, nullable=False)
    soreness_upper: Mapped[int] = mapped_column(Integer, nullable=False)
    energy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    pain_level: Mapped[int] = mapped_column(Integer, nullable=False)
    available_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="check_ins")
    runs: Mapped[list["AgentRun"]] = relationship(back_populates="check_in")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    check_in_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("daily_checkins.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="completed")
    recovery_status: Mapped[str] = mapped_column(String(20), nullable=False)
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_agents: Mapped[dict] = mapped_column(JSONB, nullable=False)
    skipped_agents: Mapped[dict] = mapped_column(JSONB, nullable=False)
    final_message: Mapped[str] = mapped_column(Text, nullable=False)
    response_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="runs")
    check_in: Mapped[DailyCheckIn] = relationship(back_populates="runs")
    decisions: Mapped[list["SupervisorDecision"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    plan_versions: Mapped[list["PlanVersion"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class SupervisorDecision(Base):
    __tablename__ = "supervisor_decisions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    agent: Mapped[str] = mapped_column(String(60), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    run: Mapped[AgentRun] = relationship(back_populates="decisions")


class PlanVersion(Base):
    __tablename__ = "plan_versions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    run: Mapped[AgentRun] = relationship(back_populates="plan_versions")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    collection: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(400), nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id"),
        nullable=False,
        index=True,
    )
    collection: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
