from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    DailyCheckIn,
    PlanVersion,
    SupervisorDecision,
    User,
    UserProfileRecord,
)
from app.schemas import DailyBriefingResponse, MorningCheckInRequest


def persist_daily_briefing(
    db: Session,
    request: MorningCheckInRequest,
    response: DailyBriefingResponse,
) -> AgentRun:
    profile = response.profile
    wearable = response.wearable

    user = db.get(User, profile.user_id)
    if user is None:
        user = User(id=profile.user_id, name=profile.name)
        db.add(user)
    else:
        user.name = profile.name

    db.merge(
        UserProfileRecord(
            user_id=profile.user_id,
            age=profile.age,
            gender=profile.gender,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            fitness_level=profile.fitness_level,
            goal=profile.goal,
            dietary_restrictions={"items": profile.dietary_restrictions},
            equipment_available={"items": profile.equipment_available},
            injury_history={"items": profile.injury_history},
        )
    )

    check_in = DailyCheckIn(
        user_id=profile.user_id,
        sleep_hours=wearable.sleep_hours,
        sleep_score=wearable.sleep_score,
        resting_heart_rate=wearable.resting_heart_rate,
        stress_level=wearable.stress_level,
        soreness_quads=wearable.soreness_quads,
        soreness_upper=wearable.soreness_upper,
        energy_level=wearable.energy_level,
        pain_level=wearable.pain_level,
        available_minutes=wearable.available_minutes,
        raw_payload=request.model_dump(mode="json"),
    )
    db.add(check_in)
    db.flush()

    run = AgentRun(
        user_id=profile.user_id,
        check_in_id=check_in.id,
        status="completed",
        recovery_status=response.recovery.status,
        readiness_score=response.recovery.readiness_score,
        selected_agents={"items": response.directives.selected_agents},
        skipped_agents={"items": response.directives.skipped_agents},
        final_message=response.final_message,
        response_snapshot=response.model_dump(mode="json"),
    )
    db.add(run)
    db.flush()

    for audit_item in response.audit:
        db.add(
            SupervisorDecision(
                run_id=run.id,
                agent=audit_item.agent,
                decision=audit_item.decision,
                evidence={"items": audit_item.evidence},
            )
        )

    if response.workout is not None:
        db.add(
            PlanVersion(
                run_id=run.id,
                user_id=profile.user_id,
                plan_type="workout",
                title=response.workout.title,
                payload=response.workout.model_dump(mode="json"),
            )
        )

    if response.nutrition is not None:
        db.add(
            PlanVersion(
                run_id=run.id,
                user_id=profile.user_id,
                plan_type="nutrition",
                title=response.nutrition.title,
                payload=response.nutrition.model_dump(mode="json"),
            )
        )

    db.commit()
    db.refresh(run)
    return run

