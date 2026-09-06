from contextlib import asynccontextmanager
import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi import Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AgentRun, KnowledgeChunk
from app.db.seed import seed_knowledge_base
from app.db.session import SessionLocal, get_db
from app.agents.nutritionist import create_nutrition_plan, create_weekly_nutrition_plan
from app.agents.trainer import create_weekly_workout_plan
from app.schemas import (
    AgentRunSummary,
    DailyBriefingResponse,
    KnowledgeChunkSummary,
    MorningCheckInRequest,
    NutritionPlan,
    SaveDailyAdjustmentRequest,
    SavedDailyAdjustmentSummary,
    SavedGeneratedPlanSummary,
    SupervisorDirectives,
    UserProfile,
    WeeklyNutritionPlan,
    WeeklyWorkoutPlan,
    WorkoutPlan,
)
from app.services.persistence import persist_daily_briefing
from app.services.daily_adjustments import (
    delete_saved_daily_adjustment,
    list_saved_daily_adjustments,
    upsert_saved_daily_adjustment,
)
from app.services.profiles import get_profile, upsert_profile
from app.services.saved_plans import delete_saved_generated_plan, list_saved_generated_plans, upsert_saved_generated_plan
from app.services.llm import LlmClient, get_llm_client
from app.services.rag import RagService
from app.services.wearable_data import WearableDataService
from app.workflow.graph import run_morning_check_in

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


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
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    llm = get_llm_client()
    llm_access = "open"
    if settings.llm_access_control_enabled and settings.demo_access_code:
        llm_access = "demo-code-protected"
    elif settings.llm_access_control_enabled and settings.environment != "local":
        llm_access = "fallback-only"

    return {
        "status": "ok",
        "persistence": "enabled" if settings.persistence_enabled else "disabled",
        "llm_provider": llm.provider,
        "llm": "enabled" if llm.enabled else "fallback",
        "llm_access": llm_access,
    }


def get_cost_safe_llm_client(
    x_demo_code: Annotated[str | None, Header(alias="X-Demo-Code")] = None,
) -> LlmClient:
    if not settings.llm_access_control_enabled:
        return get_llm_client()

    configured_code = settings.demo_access_code.strip()
    provided_code = (x_demo_code or "").strip()

    if configured_code:
        if provided_code == configured_code:
            return get_llm_client()
        logger.info("LLM disabled for request: missing or invalid demo access code.")
        return LlmClient()

    if settings.environment.lower() != "local":
        logger.info("LLM disabled for request: DEMO_ACCESS_CODE is not configured outside local mode.")
        return LlmClient()

    return get_llm_client()


@app.post("/api/check-ins/simulate", response_model=DailyBriefingResponse)
def simulate_morning_check_in(
    payload: MorningCheckInRequest,
    db: Annotated[Session, Depends(get_db)], # active connection to the database, if persistence is enabled
    llm: Annotated[LlmClient, Depends(get_cost_safe_llm_client)],
) -> DailyBriefingResponse:
    wearable = WearableDataService().sample_snapshot(payload.self_report)
    payload = payload.model_copy(update={"wearable": wearable}) # update the payload to include the sampled wearable snapshot

    if settings.persistence_enabled:
        saved_profile = get_profile(db, payload.profile.user_id)
        if saved_profile is not None: # if a saved profile exists in the database
            payload = payload.model_copy(update={"profile": saved_profile}) # use it instead of the provided profile

    briefing = run_morning_check_in(payload, db if settings.persistence_enabled else None, llm=llm)
    if settings.persistence_enabled:
        persist_daily_briefing(db, payload, briefing)
    return briefing


@app.post("/api/plans/workout/weekly", response_model=WeeklyWorkoutPlan)
def generate_weekly_workout_plan(
    profile: UserProfile,
    db: Annotated[Session, Depends(get_db)],
    llm: Annotated[LlmClient, Depends(get_cost_safe_llm_client)],
) -> WeeklyWorkoutPlan:
    if settings.persistence_enabled:
        saved_profile = get_profile(db, profile.user_id)
        if saved_profile is not None:
            profile = saved_profile
    plan = create_weekly_workout_plan(
        profile,
        RagService(db if settings.persistence_enabled else None),
        llm,
    )
    if settings.persistence_enabled:
        upsert_saved_generated_plan(
            db,
            profile=profile,
            plan_type="weekly_workout",
            title=plan.title,
            payload=plan.model_dump(mode="json"),
        )
    return plan


@app.post("/api/plans/nutrition/weekly", response_model=WeeklyNutritionPlan)
def generate_weekly_diet_plan(
    profile: UserProfile,
    db: Annotated[Session, Depends(get_db)],
    llm: Annotated[LlmClient, Depends(get_cost_safe_llm_client)],
) -> WeeklyNutritionPlan:
    if settings.persistence_enabled:
        saved_profile = get_profile(db, profile.user_id)
        if saved_profile is not None:
            profile = saved_profile
    plan = create_weekly_nutrition_plan(
        profile,
        RagService(db if settings.persistence_enabled else None),
        llm,
    )
    if settings.persistence_enabled:
        upsert_saved_generated_plan(
            db,
            profile=profile,
            plan_type="weekly_nutrition",
            title=plan.title,
            payload=plan.model_dump(mode="json"),
        )
    return plan


@app.get("/api/profile/{user_id}/generated-plans", response_model=list[SavedGeneratedPlanSummary])
def read_generated_plans(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[SavedGeneratedPlanSummary]:
    if not settings.persistence_enabled:
        return []
    return list_saved_generated_plans(db, user_id)


@app.delete("/api/profile/{user_id}/generated-plans/{plan_id}")
def delete_generated_plan(
    user_id: str,
    plan_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    if not settings.persistence_enabled:
        return {"status": "deleted"}
    deleted = delete_saved_generated_plan(db, user_id, plan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved generated plan not found.")
    return {"status": "deleted"}


@app.get("/api/profile/{user_id}/daily-adjustments", response_model=list[SavedDailyAdjustmentSummary])
def read_daily_adjustments(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: int = 14,
) -> list[SavedDailyAdjustmentSummary]:
    if not settings.persistence_enabled:
        return []
    return list_saved_daily_adjustments(db, user_id, limit)


@app.post("/api/profile/{user_id}/daily-adjustments", response_model=SavedDailyAdjustmentSummary)
def save_daily_adjustment(
    user_id: str,
    payload: SaveDailyAdjustmentRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SavedDailyAdjustmentSummary:
    briefing = payload.briefing
    if briefing.profile.user_id != user_id:
        briefing = briefing.model_copy(update={"profile": briefing.profile.model_copy(update={"user_id": user_id})})
    if not settings.persistence_enabled:
        return SavedDailyAdjustmentSummary(
            id="local-only",
            user_id=user_id,
            adjustment_date="local-only",
            current_day=briefing.current_day or "Today",
            recovery_status=briefing.recovery.status,
            readiness_score=briefing.recovery.readiness_score,
            title=f"{briefing.current_day or 'Today'} adjustment",
            payload=briefing.model_dump(mode="json"),
            updated_at="local-only",
        )
    adjustment = upsert_saved_daily_adjustment(db, briefing=briefing)
    return SavedDailyAdjustmentSummary(
        id=str(adjustment.id),
        user_id=adjustment.user_id,
        adjustment_date=adjustment.adjustment_date.isoformat(),
        current_day=adjustment.current_day,
        recovery_status=adjustment.recovery_status,
        readiness_score=adjustment.readiness_score,
        title=adjustment.title,
        payload=adjustment.payload,
        updated_at=adjustment.updated_at.isoformat(),
    )


@app.delete("/api/profile/{user_id}/daily-adjustments/{adjustment_id}")
def delete_daily_adjustment(
    user_id: str,
    adjustment_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    if not settings.persistence_enabled:
        return {"status": "deleted"}
    deleted = delete_saved_daily_adjustment(db, user_id, adjustment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved daily adjustment not found.")
    return {"status": "deleted"}


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
