from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SavedDailyAdjustment, User
from app.schemas import DailyBriefingResponse, SavedDailyAdjustmentSummary


def upsert_saved_daily_adjustment(
    db: Session,
    *,
    briefing: DailyBriefingResponse,
    adjustment_date: date | None = None,
) -> SavedDailyAdjustment:
    profile = briefing.profile
    saved_date = adjustment_date or date.today()

    user = db.get(User, profile.user_id)
    if user is None:
        user = User(id=profile.user_id, name=profile.name)
        db.add(user)
    else:
        user.name = profile.name

    existing = db.scalar(
        select(SavedDailyAdjustment)
        .where(SavedDailyAdjustment.user_id == profile.user_id)
        .where(SavedDailyAdjustment.adjustment_date == saved_date)
        .limit(1)
    )
    title = _adjustment_title(briefing)

    if existing is None:
        existing = SavedDailyAdjustment(
            user_id=profile.user_id,
            adjustment_date=saved_date,
            current_day=briefing.current_day or saved_date.strftime("%A"),
            recovery_status=briefing.recovery.status,
            readiness_score=briefing.recovery.readiness_score,
            title=title,
            payload=briefing.model_dump(mode="json"),
        )
        db.add(existing)
    else:
        existing.current_day = briefing.current_day or saved_date.strftime("%A")
        existing.recovery_status = briefing.recovery.status
        existing.readiness_score = briefing.recovery.readiness_score
        existing.title = title
        existing.payload = briefing.model_dump(mode="json")

    db.commit()
    db.refresh(existing)
    return existing


def list_saved_daily_adjustments(
    db: Session,
    user_id: str,
    limit: int = 14,
) -> list[SavedDailyAdjustmentSummary]:
    adjustments = db.scalars(
        select(SavedDailyAdjustment)
        .where(SavedDailyAdjustment.user_id == user_id)
        .order_by(SavedDailyAdjustment.adjustment_date.desc(), SavedDailyAdjustment.updated_at.desc())
        .limit(min(limit, 50))
    ).all()
    return [_to_summary(adjustment) for adjustment in adjustments]


def delete_saved_daily_adjustment(db: Session, user_id: str, adjustment_id: str) -> bool:
    try:
        parsed_adjustment_id = UUID(adjustment_id)
    except ValueError:
        return False

    adjustment = db.scalar(
        select(SavedDailyAdjustment)
        .where(SavedDailyAdjustment.user_id == user_id)
        .where(SavedDailyAdjustment.id == parsed_adjustment_id)
        .limit(1)
    )
    if adjustment is None:
        return False

    db.delete(adjustment)
    db.commit()
    return True


def _to_summary(adjustment: SavedDailyAdjustment) -> SavedDailyAdjustmentSummary:
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


def _adjustment_title(briefing: DailyBriefingResponse) -> str:
    day = briefing.current_day or "Today"
    workout_title = briefing.workout.title if briefing.workout is not None else "Rest guidance"
    return f"{day} adjustment - {workout_title}"
