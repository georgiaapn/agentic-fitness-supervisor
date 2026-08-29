from sqlalchemy.orm import Session

from app.db.models import User, UserProfileRecord
from app.schemas import UserProfile


def get_profile(db: Session, user_id: str) -> UserProfile | None:
    record = db.get(UserProfileRecord, user_id)
    if record is None:
        return None

    user = db.get(User, user_id)
    return UserProfile(
        user_id=user_id,
        name=user.name if user is not None else "Demo User",
        age=record.age,
        gender=record.gender,
        height_cm=record.height_cm,
        weight_kg=record.weight_kg,
        fitness_level=record.fitness_level,
        goal=record.goal,
        dietary_restrictions=record.dietary_restrictions.get("items", []),
        equipment_available=record.equipment_available.get("items", []),
        injury_history=record.injury_history.get("items", []),
    )


def upsert_profile(db: Session, profile: UserProfile) -> UserProfile:
    user = db.get(User, profile.user_id)
    if user is None:
        db.add(User(id=profile.user_id, name=profile.name))
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
    db.commit()
    return profile
