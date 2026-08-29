from app.agents.nutritionist import create_nutrition_plan
from app.agents.recovery import analyze_recovery
from app.agents.supervisor import coordinate_day
from app.agents.trainer import create_workout_plan
from app.schemas import DailyBriefingResponse, DecisionAuditItem, MorningCheckInRequest
from app.services.rag import RagService


def run_morning_check_in(payload: MorningCheckInRequest) -> DailyBriefingResponse:
    """Run the MVP graph.

    This is intentionally shaped like a LangGraph state transition pipeline. The next step is to
    replace this direct orchestration with a compiled LangGraph graph while keeping the node
    functions stable.
    """

    rag = RagService()
    profile = payload.profile
    wearable = payload.wearable

    recovery = analyze_recovery(wearable, rag)
    directives = coordinate_day(profile, wearable, recovery)

    workout = None
    nutrition = None

    if "trainer" in directives.selected_agents:
        workout = create_workout_plan(profile, wearable, directives, rag)
    if "nutritionist" in directives.selected_agents:
        nutrition = create_nutrition_plan(profile, directives, rag)

    audit = [
        DecisionAuditItem(
            agent="recovery",
            decision=f"Classified recovery as {recovery.status}.",
            evidence=[
                f"sleep_score={wearable.sleep_score}",
                f"soreness_quads={wearable.soreness_quads}",
                f"readiness_score={recovery.readiness_score}",
            ],
        ),
        DecisionAuditItem(
            agent="supervisor",
            decision="Issued trainer and nutrition directives from recovery constraints.",
            evidence=recovery.constraints or ["No blocking constraints detected."],
        ),
    ]

    final_message = (
        "Your plan was adjusted for recovery today. Heavy lower-body work is blocked, "
        "mobility is prioritized, and nutrition stays protein-forward."
        if recovery.status == "RED"
        else "Your readiness supports the planned training day with normal load management."
    )

    return DailyBriefingResponse(
        profile=profile,
        wearable=wearable,
        recovery=recovery,
        directives=directives,
        workout=workout,
        nutrition=nutrition,
        audit=audit,
        final_message=final_message,
    )

