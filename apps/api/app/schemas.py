from typing import Literal # to ensure that variables take specific values from a predefined set of options

from pydantic import BaseModel, Field # to ensure that variables are of the correct type and to provide default values and validation for fields


Goal = Literal["fat_loss", "hypertrophy", "strength", "general_fitness"]
FitnessLevel = Literal["beginner", "intermediate", "advanced"]
RecoveryStatus = Literal["GREEN", "YELLOW", "RED"]
AgentName = Literal["recovery", "supervisor", "trainer", "nutritionist"]

# Pydantic models for user profile, wearable data, and morning check-ins.
# - Literal: Restricts fields to predefined fixed values (type aliases).
# - Field(default_factory=...): Safely generates unique memory allocations for
#   mutable defaults (lists) per instance (default_factory), while also enforcing validation limits (ge/le) (Field).

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
    # every new UserProfile that doesn't define injury_history will have its own unique list with these default value

class WearableSnapshot(BaseModel):
    sleep_hours: float = 5.0
    sleep_score: int = Field(default=42, ge=0, le=100)
    resting_heart_rate: int = 72
    blood_oxygen_level: float = Field(default=98.0, ge=0, le=100)
    step_count: int = Field(default=5450, ge=0)
    activity_level: str = "moderately_active"
    stress_level: int = Field(default=7, ge=0, le=10)
    soreness_quads: int = Field(default=8, ge=0, le=10)
    soreness_upper: int = Field(default=3, ge=0, le=10)
    energy_level: int = Field(default=4, ge=0, le=10)
    pain_level: int = Field(default=3, ge=0, le=10)
    available_minutes: int = 35


class MorningSelfReport(BaseModel):
    soreness_quads: int = Field(default=8, ge=0, le=10)
    soreness_upper: int = Field(default=3, ge=0, le=10)
    pain_level: int = Field(default=3, ge=0, le=10)
    available_minutes: int = Field(default=35, ge=5, le=180)


class MorningCheckInRequest(BaseModel):
    profile: UserProfile = Field(default_factory=UserProfile)
    wearable: WearableSnapshot = Field(default_factory=WearableSnapshot)
    self_report: MorningSelfReport = Field(default_factory=MorningSelfReport)
    requested_plan: Literal["daily_briefing", "workout", "nutrition"] = "daily_briefing"
    # In our current implementation morning check in requests are always for the daily briefing,
    # but we may want to allow users to request just a workout or nutrition plan in the future.

# Each time an agent searches knowledge base, they return with a list of RagHits.
# For example:
# RagHit(
    # source="exercise_knowledge_base",
    # title="Dumbbell row",
    # snippet="Exercise: Dumbbell row. Equipment: dumbbell. Target: back...",
    # score=0.91,
# )
class RagHit(BaseModel):
    source: str
    title: str
    snippet: str
    score: float


class RecoveryReport(BaseModel):
    status: RecoveryStatus # RED, YELLOW, GREEN
    readiness_score: int
    summary: str # small description of the recovery status and readiness score
    constraints: list[str] # list of constraints Supervisor and the others should respect
    rag_context: list[RagHit] = Field(default_factory=list) # which recovery knowledge entries where used


class SupervisorDirectives(BaseModel): # output of the supervisor agent
    selected_agents: list[AgentName]
    skipped_agents: list[AgentName]
    trainer_directive: str # the directive for the trainer agent, e.g. "generate a workout plan for today"
    nutritionist_directive: str # the directive for the nutritionist agent, e.g. "generate a nutrition plan for today"
    rationale: str # the reasoning behind the supervisor's decision, e.g. "the user is in RED recovery status, so we will skip the trainer agent and only generate a nutrition plan"


class WorkoutPlan(BaseModel): # trainer agent output/suggestion for today, AFTER the checkin
    title: str
    duration_minutes: int
    intensity: Literal["low", "moderate", "high"]
    blocks: list[str] # daily adjustment: block = 1 exercise/section
    notes: list[str]
    rag_context: list[RagHit] = Field(default_factory=list) # which workout knowledge entries where used


class WeeklyWorkoutExercise(BaseModel): # represents a single exercise inside a weekly workout day
    name: str
    prescription: str
    notes: str | None = None


class WeeklyWorkoutDay(BaseModel): # represents a single workout day inside the weekly workout plan
    day: str
    title: str
    exercises: list[WeeklyWorkoutExercise]


class WeeklyWorkoutPlan(BaseModel): # represents the generated weekly workout plan
    title: str
    duration_minutes: int
    intensity: Literal["low", "moderate", "high"]
    days: list[WeeklyWorkoutDay]
    notes: list[str]
    rag_context: list[RagHit] = Field(default_factory=list)


class BaselineWorkoutDay(BaseModel): # today's baseline workout plan, used for checkin with the generated workout plan
    day: str
    title: str
    details: list[str]


class NutritionPlan(BaseModel): # nutrition agent output/suggestion for today, AFTER the checkin
    title: str
    calorie_target: int
    protein_g: int
    meals: list[str]
    notes: list[str]
    rag_context: list[RagHit] = Field(default_factory=list)


class WeeklyNutritionMeal(BaseModel): # represents a single meal
    meal_type: str # e.g. breakfast, lunch, dinner, snack
    name: str
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


class WeeklyNutritionDay(BaseModel): # represents a single day
    day: str
    focus: str
    meals: list[WeeklyNutritionMeal]


class BaselineNutritionDay(BaseModel): # today's baseline nutrition plan, used for checkin with the generated nutrition plan
    day: str
    focus: str
    meals: list[WeeklyNutritionMeal]


class WeeklyNutritionPlan(BaseModel): # represents a weekly nutrition plan
    title: str
    daily_calorie_target: int
    daily_protein_g: int
    days: list[WeeklyNutritionDay]
    notes: list[str]
    rag_context: list[RagHit] = Field(default_factory=list)


class SavedGeneratedPlanSummary(BaseModel): # represents a saved generated plan, either workout or nutrition
    id: str
    user_id: str # which user it belongs to
    plan_type: str # nutrition or workout
    title: str
    payload: dict # the whole plan, either workout or nutrition, in JSON/dict format (WeeklyWorkoutPlan or WeeklyNutritionPlan)
    updated_at: str


class SavedDailyAdjustmentSummary(BaseModel):
    id: str
    user_id: str
    adjustment_date: str
    current_day: str
    recovery_status: str # RED, YELLOW, GREEN
    readiness_score: int
    title: str
    payload: dict # DailyBriefingResponse saved in JSON/dict format
    updated_at: str


class DecisionAuditItem(BaseModel): # audit trail about what each agent did and why, for transparency and debugging
    agent: AgentName
    decision: str
    evidence: list[str]


class DailyBriefingResponse(BaseModel): # final output of morning checkin
    profile: UserProfile # user profile that was used
    wearable: WearableSnapshot # wearable snapshot that was used
    current_day: str | None = None
    baseline_workout: BaselineWorkoutDay | None = None
    baseline_nutrition: BaselineNutritionDay | None = None
    recovery: RecoveryReport
    directives: SupervisorDirectives
    workout: WorkoutPlan | None
    nutrition: NutritionPlan | None
    audit: list[DecisionAuditItem]
    final_message: str


class SaveDailyAdjustmentRequest(BaseModel): # input/request body for save adjustment
    briefing: DailyBriefingResponse


class AgentRunSummary(BaseModel): # summary of an older agent run, useful for GET /api/runs
    id: str
    user_id: str
    recovery_status: str
    readiness_score: int
    final_message: str
    created_at: str


class KnowledgeChunkSummary(BaseModel): # summary of a knowledge chunk from our database
    id: str
    collection: str
    title: str
    content: str
    metadata: dict
