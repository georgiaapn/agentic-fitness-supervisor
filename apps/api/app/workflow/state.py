from typing import Literal, TypedDict

from app.schemas import (
    DecisionAuditItem,
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
    profile: UserProfile
    wearable: WearableSnapshot
    recovery: RecoveryReport
    directives: SupervisorDirectives
    workout: WorkoutPlan | None
    nutrition: NutritionPlan | None
    audit: list[DecisionAuditItem]
    final_message: str
