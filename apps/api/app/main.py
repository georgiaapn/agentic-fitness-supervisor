from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.init_db import init_db
from app.db.models import AgentRun
from app.db.session import get_db
from app.schemas import AgentRunSummary, DailyBriefingResponse, MorningCheckInRequest
from app.services.persistence import persist_daily_briefing
from app.workflow.graph import run_morning_check_in


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.persistence_enabled:
        init_db()
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
    briefing = run_morning_check_in(payload)
    if settings.persistence_enabled:
        persist_daily_briefing(db, payload, briefing)
    return briefing


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
