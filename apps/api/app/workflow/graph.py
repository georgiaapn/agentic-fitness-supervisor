from datetime import datetime

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.agents.nutritionist import create_nutrition_plan
from app.agents.recovery import analyze_recovery
from app.agents.supervisor import coordinate_day
from app.agents.trainer import create_workout_plan
from app.schemas import (
    BaselineNutritionDay,
    BaselineWorkoutDay,
    DailyBriefingResponse,
    DecisionAuditItem,
    MorningCheckInRequest,
    WeeklyNutritionPlan,
    WeeklyWorkoutPlan,
)
from app.services.llm import LlmClient, get_llm_client
from app.services.rag import RagService
from app.services.saved_plans import get_saved_generated_plan
from app.workflow.state import FitnessGraphState, SpecialistNode


def load_context_node(state: FitnessGraphState) -> FitnessGraphState:
    request = state["request"]
    current_day = datetime.now().strftime("%A")
    baseline_workout = _load_baseline_workout_day(state.get("db"), request.profile.user_id, current_day)
    baseline_nutrition = _load_baseline_nutrition_day(state.get("db"), request.profile.user_id, current_day)
    return {
        "profile": request.profile,
        "wearable": request.wearable,
        "current_day": current_day,
        "baseline_workout": baseline_workout,
        "baseline_nutrition": baseline_nutrition,
        "workout": None,
        "nutrition": None,
        "audit": [],
    }


def recovery_node(state: FitnessGraphState) -> FitnessGraphState:
    rag = RagService(state.get("db"))
    recovery = analyze_recovery(state["wearable"], rag)
    audit = [
        *state.get("audit", []),
        DecisionAuditItem(
            agent="recovery",
            decision=f"Classified recovery as {recovery.status}.",
            evidence=[
                f"sleep_score={state['wearable'].sleep_score}",
                f"soreness_quads={state['wearable'].soreness_quads}",
                f"readiness_score={recovery.readiness_score}",
            ],
        ),
    ]
    return {"recovery": recovery, "audit": audit}

# at this point the theoritical decision taken by coordinate_day is oficially integrated in the flow
def supervisor_node(state: FitnessGraphState) -> FitnessGraphState:
    directives = coordinate_day(
        state["profile"],
        state["wearable"],
        state["recovery"],
        current_day=state.get("current_day"),
        baseline_workout=state.get("baseline_workout"),
        baseline_nutrition=state.get("baseline_nutrition"),
    )
    # record the supervisor's decision in the audit trail
    audit = [
        *state.get("audit", []),
        DecisionAuditItem(
            agent="supervisor",
            decision="Selected specialist agents and issued planning directives.",
            evidence=[
                *(state["recovery"].constraints or ["No blocking constraints detected."]),
                *(_baseline_audit_evidence(state)),
            ],
        ),
    ]
    return {"directives": directives, "audit": audit}


def route_specialists(state: FitnessGraphState) -> list[SpecialistNode]:
    if "trainer" not in state["directives"].selected_agents:
        return ["nutritionist_solo"]
    return ["trainer_agent", "nutritionist_agent"]


def trainer_node(state: FitnessGraphState) -> FitnessGraphState:
    rag = RagService(state.get("db")) # create a RAG service instance for the trainer agent to use
    workout = create_workout_plan(
        state["profile"],
        state["wearable"],
        state["directives"],
        rag,
        state.get("llm") or get_llm_client(),
        baseline_workout=state.get("baseline_workout"),
        current_day=state.get("current_day"),
    )
    return {"workout": workout}


def nutritionist_node(state: FitnessGraphState) -> FitnessGraphState:
    rag = RagService(state.get("db")) # create a RAG service instance for the nutritionist agent to use
    nutrition = create_nutrition_plan(
        state["profile"],
        state["directives"],
        rag,
        state.get("llm") or get_llm_client(),
        baseline_nutrition=state.get("baseline_nutrition"),
        current_day=state.get("current_day"),
    )
    return {"nutrition": nutrition}

# this node aggregates the outputs of the specialist agents and produces a final message for the user
def aggregate_node(state: FitnessGraphState) -> FitnessGraphState:
    recovery = state["recovery"]
    final_message = (
        "Your plan was adjusted for recovery today. Fatiguing work is reduced, "
        "recovery-safe movement is prioritized, and nutrition stays protein-forward."
        if recovery.status == "RED"
        else "Your readiness supports the planned training day with normal load management."
    )
    return {"final_message": final_message}


def build_fitness_graph():
    graph = StateGraph(FitnessGraphState)
    graph.add_node("load_context", load_context_node)
    graph.add_node("recovery_agent", recovery_node)
    graph.add_node("supervisor_agent", supervisor_node)
    graph.add_node("trainer_agent", trainer_node)
    graph.add_node("nutritionist_agent", nutritionist_node)
    graph.add_node("nutritionist_solo", nutritionist_node)
    graph.add_node("aggregate", aggregate_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "recovery_agent")
    graph.add_edge("recovery_agent", "supervisor_agent")
    graph.add_conditional_edges(
        "supervisor_agent",
        route_specialists,
    )
    graph.add_edge(["trainer_agent", "nutritionist_agent"], "aggregate")
    graph.add_edge("nutritionist_solo", "aggregate")
    graph.add_edge("aggregate", END)
    return graph.compile()


fitness_graph = build_fitness_graph()


def run_morning_check_in(
    payload: MorningCheckInRequest,
    db: object | None = None,
    llm: LlmClient | None = None,
) -> DailyBriefingResponse:
    final_state = fitness_graph.invoke({"request": payload, "db": db, "llm": llm or get_llm_client()})

    return DailyBriefingResponse(
        profile=final_state["profile"],
        wearable=final_state["wearable"],
        current_day=final_state.get("current_day"),
        baseline_workout=final_state.get("baseline_workout"),
        baseline_nutrition=final_state.get("baseline_nutrition"),
        recovery=final_state["recovery"],
        directives=final_state["directives"],
        workout=final_state.get("workout"),
        nutrition=final_state.get("nutrition"),
        audit=final_state["audit"],
        final_message=final_state["final_message"],
    )


def _load_baseline_workout_day(
    db: object | None,
    user_id: str,
    current_day: str,
) -> BaselineWorkoutDay | None:
    if db is None:
        return None
    saved = get_saved_generated_plan(db, user_id, "weekly_workout")
    if saved is None:
        return None
    try:
        plan = WeeklyWorkoutPlan.model_validate(saved.payload)
    except ValidationError:
        return None
    return _workout_day_from_plan(plan, current_day)


def _load_baseline_nutrition_day(
    db: object | None,
    user_id: str,
    current_day: str,
) -> BaselineNutritionDay | None:
    if db is None:
        return None
    saved = get_saved_generated_plan(db, user_id, "weekly_nutrition")
    if saved is None:
        return None
    try:
        plan = WeeklyNutritionPlan.model_validate(saved.payload)
    except ValidationError:
        return None
    day = next((item for item in plan.days if item.day.lower() == current_day.lower()), None)
    if day is None:
        return None
    return BaselineNutritionDay(day=day.day, focus=day.focus, meals=day.meals)

# searches in a weekly plan for the current day and returns the BaselineWorkoutDay
def _workout_day_from_plan(plan: WeeklyWorkoutPlan, current_day: str) -> BaselineWorkoutDay | None:
    matching_day = next((day for day in plan.days if day.day.lower() == current_day.lower()), None)
    if matching_day is None:
        return None
    details = [
        f"{exercise.name} {exercise.prescription}{f' ({exercise.notes})' if exercise.notes else ''}"
        for exercise in matching_day.exercises
    ]
    return BaselineWorkoutDay(day=matching_day.day, title=matching_day.title, details=details)


def _baseline_audit_evidence(state: FitnessGraphState) -> list[str]:
    evidence = []
    if state.get("baseline_workout") is not None:
        evidence.append(f"today_workout={state['baseline_workout'].title}")
    if state.get("baseline_nutrition") is not None:
        evidence.append(f"today_nutrition={state['baseline_nutrition'].focus}")
    return evidence
