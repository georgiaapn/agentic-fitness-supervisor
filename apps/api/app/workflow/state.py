from typing import Any, Literal, TypedDict

from app.schemas import (
    DecisionAuditItem,
    BaselineNutritionDay,
    BaselineWorkoutDay,
    MorningCheckInRequest,
    NutritionPlan,
    RecoveryReport,
    SupervisorDirectives,
    UserProfile,
    WearableSnapshot,
    WorkoutPlan,
)


SpecialistNode = Literal["trainer_agent", "nutritionist_agent", "nutritionist_solo"]


class FitnessGraphState(TypedDict, total=False):
    request: MorningCheckInRequest
    db: Any
    profile: UserProfile
    wearable: WearableSnapshot
    current_day: str
    baseline_workout: BaselineWorkoutDay | None
    baseline_nutrition: BaselineNutritionDay | None
    recovery: RecoveryReport
    directives: SupervisorDirectives
    workout: WorkoutPlan | None
    nutrition: NutritionPlan | None
    audit: list[DecisionAuditItem]
    final_message: str
