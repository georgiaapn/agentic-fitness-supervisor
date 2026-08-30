from app.schemas import RecoveryReport, WearableSnapshot
from app.services.rag import RagService


def analyze_recovery(wearable: WearableSnapshot, rag: RagService) -> RecoveryReport:
    constraints: list[str] = []
    readiness = 100

    readiness -= max(0, 50 - wearable.sleep_score)
    readiness -= wearable.stress_level * 2
    readiness -= wearable.soreness_quads * 3
    readiness -= max(0, wearable.resting_heart_rate - 60)
    readiness -= max(0, 95 - int(wearable.blood_oxygen_level)) * 4
    if wearable.step_count >= 12000 and wearable.activity_level == "highly_active":
        readiness -= 8
    readiness = max(0, min(100, readiness))

    if wearable.sleep_score < 50:
        constraints.append("Avoid heavy compound lifting after low sleep readiness.")
    if wearable.soreness_quads >= 7:
        constraints.append("Block heavy lower-body loading and quad-dominant volume.")
    if wearable.blood_oxygen_level < 94:
        constraints.append("Keep intensity low because blood oxygen is below the normal demo threshold.")
    if wearable.step_count >= 12000 and wearable.activity_level == "highly_active":
        constraints.append("Reduce extra lower-body volume after a high-activity day.")
    if wearable.pain_level >= 8:
        constraints.append("Escalate to safety guidance and avoid training through pain.")

    if readiness < 50 or wearable.pain_level >= 8:
        status = "RED"
    elif readiness < 70:
        status = "YELLOW"
    else:
        status = "GREEN"

    summary = (
        "High fatigue detected from low sleep and quad soreness."
        if status == "RED"
        else "Readiness is acceptable with normal load management."
    )

    return RecoveryReport(
        status=status,
        readiness_score=readiness,
        summary=summary,
        constraints=constraints,
        rag_context=rag.recovery_protocols(wearable),
    )
