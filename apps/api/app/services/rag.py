from app.schemas import RagHit, UserProfile, WearableSnapshot


class RagService:
    """MVP retrieval facade.

    Replace these in-memory fixtures with pgvector similarity search once the database layer lands.
    """

    def recovery_protocols(self, wearable: WearableSnapshot) -> list[RagHit]:
        if wearable.sleep_score < 50:
            return [
                RagHit(
                    source="recovery_knowledge_base",
                    title="Low sleep readiness protocol",
                    snippet="Low sleep plus elevated soreness should reduce intensity and prioritize mobility.",
                    score=0.91,
                )
            ]
        return []

    def mobility_exercises(self, profile: UserProfile) -> list[RagHit]:
        return [
            RagHit(
                source="exercise_knowledge_base",
                title="Lower-body mobility reset",
                snippet="Cat-cow, 90/90 hip switches, couch stretch, and ankle rocks are low-load options.",
                score=0.88,
            ),
            RagHit(
                source="exercise_knowledge_base",
                title="Knee-friendly movement substitutions",
                snippet="Use controlled step-ups, Spanish squat isometrics, or bike intervals when knee irritation appears.",
                score=0.81,
            ),
        ]

    def recovery_meals(self, profile: UserProfile) -> list[RagHit]:
        return [
            RagHit(
                source="nutrition_knowledge_base",
                title="Recovery day protein distribution",
                snippet="Distribute protein across 3 to 4 meals and include colorful produce and omega-3 sources.",
                score=0.9,
            ),
            RagHit(
                source="nutrition_knowledge_base",
                title="Anti-inflammatory meal tags",
                snippet="Olive oil, berries, leafy greens, legumes, yogurt, and fatty fish fit recovery-focused meals.",
                score=0.84,
            ),
        ]

