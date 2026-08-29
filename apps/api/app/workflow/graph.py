from langgraph.graph import END, START, StateGraph

from app.agents.nutritionist import create_nutrition_plan
from app.agents.recovery import analyze_recovery
from app.agents.supervisor import coordinate_day
from app.agents.trainer import create_workout_plan
from app.schemas import DailyBriefingResponse, DecisionAuditItem, MorningCheckInRequest
from app.services.rag import RagService
from app.workflow.state import FitnessGraphState, SpecialistNode


def load_context_node(state: FitnessGraphState) -> FitnessGraphState:
    request = state["request"]
    return {
        "profile": request.profile,
        "wearable": request.wearable,
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


def supervisor_node(state: FitnessGraphState) -> FitnessGraphState:
    directives = coordinate_day(state["profile"], state["wearable"], state["recovery"])
    audit = [
        *state.get("audit", []),
        DecisionAuditItem(
            agent="supervisor",
            decision="Selected specialist agents and issued planning directives.",
            evidence=state["recovery"].constraints or ["No blocking constraints detected."],
        ),
    ]
    return {"directives": directives, "audit": audit}


def route_specialists(state: FitnessGraphState) -> list[SpecialistNode]:
    if "trainer" not in state["directives"].selected_agents:
        return ["nutritionist_solo"]
    return ["trainer_agent", "nutritionist_agent"]


def trainer_node(state: FitnessGraphState) -> FitnessGraphState:
    rag = RagService(state.get("db"))
    workout = create_workout_plan(state["profile"], state["wearable"], state["directives"], rag)
    return {"workout": workout}


def nutritionist_node(state: FitnessGraphState) -> FitnessGraphState:
    rag = RagService(state.get("db"))
    nutrition = create_nutrition_plan(state["profile"], state["directives"], rag)
    return {"nutrition": nutrition}


def aggregate_node(state: FitnessGraphState) -> FitnessGraphState:
    recovery = state["recovery"]
    final_message = (
        "Your plan was adjusted for recovery today. Heavy lower-body work is blocked, "
        "mobility is prioritized, and nutrition stays protein-forward."
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
) -> DailyBriefingResponse:
    final_state = fitness_graph.invoke({"request": payload, "db": db})

    return DailyBriefingResponse(
        profile=final_state["profile"],
        wearable=final_state["wearable"],
        recovery=final_state["recovery"],
        directives=final_state["directives"],
        workout=final_state.get("workout"),
        nutrition=final_state.get("nutrition"),
        audit=final_state["audit"],
        final_message=final_state["final_message"],
    )
