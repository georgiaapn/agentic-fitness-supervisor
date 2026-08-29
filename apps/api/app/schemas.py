from typing import Literal

from pydantic import BaseModel, Field


Goal = Literal["fat_loss", "hypertrophy", "strength", "general_fitness"]
FitnessLevel = Literal["beginner", "intermediate", "advanced"]
RecoveryStatus = Literal["GREEN", "YELLOW", "RED"]
AgentName = Literal["recovery", "supervisor", "trainer", "nutritionist"]


class UserProfile(BaseModel):
    user_id: str = "demo-user"
    name: str = "George"
    age: int = 31
    gender: Literal["male", "female", "other"] = "male"
    height_cm: int = 178
    weight_kg: float = 82.0
    fitness_level: FitnessLevel = "intermediate"
    goal: Goal = "hypertrophy"
    dietary_restrictions: list[str] = Field(default_factory=lambda: ["no shellfish"])
    equipment_available: list[str] = Field(default_factory=lambda: ["barbell", "dumbbells", "bands"])
    injury_history: list[str] = Field(default_factory=lambda: ["occasional right knee irritation"])


class WearableSnapshot(BaseModel):
    sleep_hours: float = 5.0
    sleep_score: int = Field(default=42, ge=0, le=100)
    resting_heart_rate: int = 72
    stress_level: int = Field(default=7, ge=0, le=10)
    soreness_quads: int = Field(default=8, ge=0, le=10)
    soreness_upper: int = Field(default=3, ge=0, le=10)
    energy_level: int = Field(default=4, ge=0, le=10)
    pain_level: int = Field(default=3, ge=0, le=10)
    available_minutes: int = 35


class MorningCheckInRequest(BaseModel):
    profile: UserProfile = Field(default_factory=UserProfile)
    wearable: WearableSnapshot = Field(default_factory=WearableSnapshot)
    requested_plan: Literal["daily_briefing", "workout", "nutrition"] = "daily_briefing"


class RagHit(BaseModel):
    source: str
    title: str
    snippet: str
    score: float


class RecoveryReport(BaseModel):
    status: RecoveryStatus
    readiness_score: int
    summary: str
    constraints: list[str]
    rag_context: list[RagHit] = Field(default_factory=list)


class SupervisorDirectives(BaseModel):
    selected_agents: list[AgentName]
    skipped_agents: list[AgentName]
    trainer_directive: str
    nutritionist_directive: str
    rationale: str


class WorkoutPlan(BaseModel):
    title: str
    duration_minutes: int
    intensity: Literal["low", "moderate", "high"]
    blocks: list[str]
    notes: list[str]
    rag_context: list[RagHit] = Field(default_factory=list)


class NutritionPlan(BaseModel):
    title: str
    calorie_target: int
    protein_g: int
    meals: list[str]
    notes: list[str]
    rag_context: list[RagHit] = Field(default_factory=list)


class DecisionAuditItem(BaseModel):
    agent: AgentName
    decision: str
    evidence: list[str]


class DailyBriefingResponse(BaseModel):
    profile: UserProfile
    wearable: WearableSnapshot
    recovery: RecoveryReport
    directives: SupervisorDirectives
    workout: WorkoutPlan | None
    nutrition: NutritionPlan | None
    audit: list[DecisionAuditItem]
    final_message: str


class AgentRunSummary(BaseModel):
    id: str
    user_id: str
    recovery_status: str
    readiness_score: int
    final_message: str
    created_at: str


class ProfileResponse(UserProfile):
    pass
