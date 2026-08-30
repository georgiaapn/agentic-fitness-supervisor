import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk
from app.schemas import RagHit, UserProfile, WearableSnapshot


class RagService:
    """Retrieval facade for agent knowledge.

    Uses seeded PostgreSQL knowledge chunks when a DB session is available. The scoring is lexical
    for now, while the schema is ready for pgvector embeddings in the next iteration.
    """

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def recovery_protocols(self, wearable: WearableSnapshot) -> list[RagHit]:
        if self.db is not None:
            query = "low sleep soreness fatigue recovery deload"
            if wearable.resting_heart_rate > 70:
                query += " elevated resting heart rate"
            hits = self._search("recovery_knowledge_base", query)
            if hits:
                return hits

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

    def mobility_exercises(self, profile: UserProfile, recovery_safe: bool = False) -> list[RagHit]:
        if self.db is not None:
            query = (
                "upper legs lower legs body weight assisted band quads hamstrings glutes "
                "calves stretch mobility soreness recovery knee low load"
            )
            if profile.injury_history:
                query += " " + " ".join(profile.injury_history)
            hits = self._search(
                "exercise_knowledge_base",
                query,
                limit=5,
                prefer_terms=["stretch", "mobility", "assisted", "body weight", "rotation"],
                avoid_terms=_recovery_exercise_avoid_terms() if recovery_safe else None,
                required_any_terms=["stretch", "mobility", "rotation"] if recovery_safe else None,
            )
            if hits:
                return hits

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
        if self.db is not None:
            query = "recovery protein anti inflammatory meals rest day"
            if profile.dietary_restrictions:
                query += " " + " ".join(profile.dietary_restrictions)
            hits = self._search("nutrition_knowledge_base", query)
            if hits:
                return hits

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

    def _search(
        self,
        collection: str,
        query: str,
        limit: int = 3,
        prefer_terms: list[str] | None = None,
        avoid_terms: list[str] | None = None,
        required_any_terms: list[str] | None = None,
    ) -> list[RagHit]:
        if self.db is None:
            return []

        chunks = self.db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.collection == collection)
            .order_by(KnowledgeChunk.created_at.asc())
        ).all()
        query_terms = _terms(query)

        scored: list[tuple[float, KnowledgeChunk]] = []
        for chunk in chunks:
            haystack = " ".join(
                [
                    chunk.title,
                    chunk.content,
                    " ".join(str(value) for value in chunk.metadata_.values()),
                ]
            ).lower()
            title = chunk.title.lower()
            if avoid_terms and any(term in title for term in avoid_terms):
                continue
            if required_any_terms and not any(term in haystack for term in required_any_terms):
                continue

            matches = sum(1 for term in query_terms if term in haystack)
            if matches:
                preference_boost = _preference_boost(haystack, prefer_terms)
                scored.append(((matches / max(len(query_terms), 1)) + preference_boost, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RagHit(
                source=collection,
                title=chunk.title,
                snippet=chunk.content,
                score=round(score, 2),
            )
            for score, chunk in scored[:limit]
        ]


def _terms(value: str) -> list[str]:
    return [term for term in re.findall(r"[a-zA-Z0-9_]+", value.lower()) if len(term) > 2]


def _preference_boost(haystack: str, prefer_terms: list[str] | None) -> float:
    if not prefer_terms:
        return 0.0
    matches = sum(1 for term in prefer_terms if term in haystack)
    return min(matches * 0.08, 0.24)


def _recovery_exercise_avoid_terms() -> list[str]:
    return [
        "deadlift",
        "jump",
        "lunge",
        "press",
        "squat",
        "weighted",
    ]
