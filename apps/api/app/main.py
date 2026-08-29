from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AgentRun, KnowledgeChunk
from app.db.seed import seed_knowledge_base
from app.db.session import SessionLocal, get_db
from app.schemas import (
    AgentRunSummary,
    DailyBriefingResponse,
    KnowledgeChunkSummary,
    MorningCheckInRequest,
    UserProfile,
)
from app.services.persistence import persist_daily_briefing
from app.services.profiles import get_profile, upsert_profile
from app.workflow.graph import run_morning_check_in


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.persistence_enabled:
        with SessionLocal() as db:
            seed_knowledge_base(db)
    yield


app = FastAPI(
    title="Agentic Fitness Supervisor API",
    description="Multi-agent RAG workflow for adaptive fitness coaching.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "persistence": "enabled" if settings.persistence_enabled else "disabled",
    }


@app.post("/api/check-ins/simulate", response_model=DailyBriefingResponse)
def simulate_morning_check_in(
    payload: MorningCheckInRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DailyBriefingResponse:
    if settings.persistence_enabled:
        saved_profile = get_profile(db, payload.profile.user_id)
        if saved_profile is not None:
            payload = payload.model_copy(update={"profile": saved_profile})

    briefing = run_morning_check_in(payload, db if settings.persistence_enabled else None)
    if settings.persistence_enabled:
        persist_daily_briefing(db, payload, briefing)
    return briefing


@app.get("/api/profile/{user_id}", response_model=UserProfile)
def read_profile(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> UserProfile:
    if settings.persistence_enabled:
        saved_profile = get_profile(db, user_id)
        if saved_profile is not None:
            return saved_profile
    return UserProfile(user_id=user_id)


@app.put("/api/profile/{user_id}", response_model=UserProfile)
def update_profile(
    user_id: str,
    profile: UserProfile,
    db: Annotated[Session, Depends(get_db)],
) -> UserProfile:
    profile = profile.model_copy(update={"user_id": user_id})
    if not settings.persistence_enabled:
        return profile
    return upsert_profile(db, profile)


@app.get("/api/agent-runs", response_model=list[AgentRunSummary])
def list_agent_runs(
    db: Annotated[Session, Depends(get_db)],
    limit: int = 10,
) -> list[AgentRunSummary]:
    if not settings.persistence_enabled:
        return []

    statement = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(min(limit, 50))
    runs = db.scalars(statement).all()
    return [
        AgentRunSummary(
            id=str(run.id),
            user_id=run.user_id,
            recovery_status=run.recovery_status,
            readiness_score=run.readiness_score,
            final_message=run.final_message,
            created_at=run.created_at.isoformat(),
        )
        for run in runs
    ]


@app.get("/api/knowledge-chunks", response_model=list[KnowledgeChunkSummary])
def list_knowledge_chunks(
    db: Annotated[Session, Depends(get_db)],
    collection: str | None = None,
    limit: int = 20,
) -> list[KnowledgeChunkSummary]:
    if not settings.persistence_enabled:
        return []

    statement = select(KnowledgeChunk).order_by(KnowledgeChunk.created_at.asc()).limit(min(limit, 100))
    if collection is not None:
        statement = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.collection == collection)
            .order_by(KnowledgeChunk.created_at.asc())
            .limit(min(limit, 100))
        )

    chunks = db.scalars(statement).all()
    return [
        KnowledgeChunkSummary(
            id=str(chunk.id),
            collection=chunk.collection,
            title=chunk.title,
            content=chunk.content,
            metadata=chunk.metadata_,
        )
        for chunk in chunks
    ]
