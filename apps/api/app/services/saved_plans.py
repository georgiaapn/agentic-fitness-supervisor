from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SavedGeneratedPlan, User
from app.schemas import SavedGeneratedPlanSummary, UserProfile


def upsert_saved_generated_plan(
    db: Session,
    *,
    profile: UserProfile,
    plan_type: str,
    title: str,
    payload: dict,
) -> SavedGeneratedPlan:
    user = db.get(User, profile.user_id)
    if user is None:
        user = User(id=profile.user_id, name=profile.name)
        db.add(user)
    else:
        user.name = profile.name

    existing = db.scalar(
        select(SavedGeneratedPlan)
        .where(SavedGeneratedPlan.user_id == profile.user_id)
        .where(SavedGeneratedPlan.plan_type == plan_type)
        .limit(1)
    )
    if existing is None:
        existing = SavedGeneratedPlan(
            user_id=profile.user_id,
            plan_type=plan_type,
            title=title,
            payload=payload,
        )
        db.add(existing)
    else:
        existing.title = title
        existing.payload = payload

    db.commit()
    db.refresh(existing)
    return existing


def list_saved_generated_plans(db: Session, user_id: str) -> list[SavedGeneratedPlanSummary]:
    plans = db.scalars(
        select(SavedGeneratedPlan)
        .where(SavedGeneratedPlan.user_id == user_id)
        .order_by(SavedGeneratedPlan.updated_at.desc())
    ).all()
    return [
        SavedGeneratedPlanSummary(
            id=str(plan.id),
            user_id=plan.user_id,
            plan_type=plan.plan_type,
            title=plan.title,
            payload=plan.payload,
            updated_at=plan.updated_at.isoformat(),
        )
        for plan in plans
    ]


def get_saved_generated_plan(db: Session, user_id: str, plan_type: str) -> SavedGeneratedPlan | None:
    return db.scalar(
        select(SavedGeneratedPlan)
        .where(SavedGeneratedPlan.user_id == user_id)
        .where(SavedGeneratedPlan.plan_type == plan_type)
        .limit(1)
    )
