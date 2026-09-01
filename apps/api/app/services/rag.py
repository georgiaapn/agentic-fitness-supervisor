import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk
from app.schemas import RagHit, UserProfile, WearableSnapshot
from app.services.embeddings import EmbeddingProviderUnavailable, embed_query, vector_literal


class RagService:
    """Retrieval facade for agent knowledge.

    Uses pgvector similarity when embeddings exist, with a lexical fallback for local setup.
    """

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def recovery_protocols(self, wearable: WearableSnapshot) -> list[RagHit]:
        if self.db is not None:
            query_parts = ["recovery readiness protocol fatigue load management"]
            if wearable.sleep_score < 50 or wearable.sleep_hours < 6:
                query_parts.append("low sleep sleep deprivation poor recovery")
            if wearable.soreness_quads >= 7 or wearable.soreness_upper >= 7:
                query_parts.append("high local soreness DOMS deload")
            if wearable.resting_heart_rate > 70:
                query_parts.append("elevated resting heart rate")
            if wearable.blood_oxygen_level < 94:
                query_parts.append("low blood oxygen SpO2 below threshold")
            if wearable.stress_level >= 7:
                query_parts.append("high stress downshift")
            if wearable.step_count >= 12000:
                query_parts.append("high step count high activity lower-body volume reduction")
            if wearable.pain_level >= 6:
                query_parts.append("pain safety stop rule sharp pain swelling limping")

            query = " ".join(query_parts)
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

    def mobility_exercises(
        self,
        profile: UserProfile,
        recovery_safe: bool = False,
        focus: str = "general",
    ) -> list[RagHit]:
        if self.db is not None:
            query = _mobility_query(focus)
            if profile.injury_history:
                query += " " + " ".join(profile.injury_history)
            hits = self._search(
                "exercise_knowledge_base",
                query,
                limit=5,
                prefer_terms=_mobility_prefer_terms(focus),
                avoid_terms=_recovery_exercise_avoid_terms() if recovery_safe else None,
                required_any_terms=_mobility_required_terms(focus) if recovery_safe else None,
                allowed_equipment=_allowed_exercise_equipment(profile),
            )
            if hits:
                return hits

        return _fallback_mobility_hits(focus)

    def training_exercises(self, profile: UserProfile) -> list[RagHit]:
        if self.db is not None:
            query = _training_query(profile)
            hits = self._search(
                "exercise_knowledge_base",
                query,
                limit=8,
                prefer_terms=_training_prefer_terms(profile),
                avoid_terms=_training_avoid_terms(),
                allowed_equipment=_allowed_exercise_equipment(profile),
            )
            if hits:
                return hits

        return _fallback_training_hits(profile)

    def recovery_meals(self, profile: UserProfile) -> list[RagHit]:
        if self.db is not None:
            query = "healthy recipe high protein recovery balanced meal diet cuisine"
            if profile.goal == "fat_loss":
                query += " dash mediterranean lean high satiety"
            elif profile.goal == "hypertrophy":
                query += " high protein balanced carbs training support"
            elif profile.goal == "strength":
                query += " high protein carbs training support"
            else:
                query += " balanced healthy"
            if profile.dietary_restrictions:
                query += " " + " ".join(profile.dietary_restrictions)
            hits = self._search(
                "nutrition_knowledge_base",
                query,
                limit=4,
                prefer_terms=_nutrition_prefer_terms(profile),
                avoid_terms=_nutrition_avoid_terms(profile),
            )
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
        allowed_equipment: set[str] | None = None,
    ) -> list[RagHit]:
        if self.db is None:
            return []

        vector_hits = self._vector_search(
            collection,
            query,
            limit=limit,
            avoid_terms=avoid_terms,
            required_any_terms=required_any_terms,
            allowed_equipment=allowed_equipment,
        )
        if vector_hits:
            return vector_hits

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
            if not _allowed_by_constraints(
                title=chunk.title,
                haystack=haystack,
                avoid_terms=avoid_terms,
                required_any_terms=required_any_terms,
                allowed_equipment=allowed_equipment,
                metadata=chunk.metadata_,
            ):
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

    def _vector_search(
        self,
        collection: str,
        query: str,
        limit: int,
        avoid_terms: list[str] | None,
        required_any_terms: list[str] | None,
        allowed_equipment: set[str] | None,
    ) -> list[RagHit]:
        if self.db is None:
            return []
        if not self._collection_has_embeddings(collection):
            return []

        try:
            embedding = vector_literal(embed_query(query)) # turn query into embedding too
        except EmbeddingProviderUnavailable:
            return []

        rows = self.db.execute(
            text(
                "SELECT title, content, collection, "
                "metadata, "
                "1 - (embedding <=> CAST(:embedding AS vector)) AS score "
                "FROM knowledge_chunks "
                "WHERE collection = :collection AND embedding IS NOT NULL "
                "ORDER BY embedding <=> CAST(:embedding AS vector) "
                "LIMIT :candidate_limit"
            ),
            {
                "collection": collection,
                "embedding": embedding,
                "candidate_limit": max(limit * 10, 20),
            },
        ).mappings()

        hits: list[RagHit] = []
        for row in rows:
            haystack = f"{row['title']} {row['content']}".lower()
            if not _allowed_by_constraints(
                title=str(row["title"]),
                haystack=haystack,
                avoid_terms=avoid_terms,
                required_any_terms=required_any_terms,
                allowed_equipment=allowed_equipment,
                metadata=dict(row["metadata"] or {}),
            ):
                continue
            hits.append(
                RagHit(
                    source=str(row["collection"]),
                    title=str(row["title"]),
                    snippet=str(row["content"]),
                    score=round(float(row["score"]), 2),
                )
            )
            if len(hits) >= limit:
                break

        return hits

    def _collection_has_embeddings(self, collection: str) -> bool:
        if self.db is None:
            return False

        return bool(
            self.db.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM knowledge_chunks "
                    "WHERE collection = :collection AND embedding IS NOT NULL"
                    ")"
                ),
                {"collection": collection},
            )
        )


def _terms(value: str) -> list[str]:
    return [term for term in re.findall(r"[a-zA-Z0-9_]+", value.lower()) if len(term) > 2]


def _allowed_by_constraints(
    title: str,
    haystack: str,
    avoid_terms: list[str] | None,
    required_any_terms: list[str] | None,
    allowed_equipment: set[str] | None = None,
    metadata: dict | None = None,
) -> bool:
    lowered_title = title.lower()
    if avoid_terms and any(term in lowered_title for term in avoid_terms):
        return False
    if required_any_terms and not any(term in haystack for term in required_any_terms):
        return False
    if allowed_equipment is not None and not _equipment_allowed(metadata, allowed_equipment):
        return False
    return True


def _preference_boost(haystack: str, prefer_terms: list[str] | None) -> float:
    if not prefer_terms:
        return 0.0
    matches = sum(1 for term in prefer_terms if term in haystack)
    return min(matches * 0.08, 0.24)


def _mobility_query(focus: str) -> str:
    if focus == "upper":
        return (
            "upper body shoulders chest back thoracic scapular neck arms band assisted "
            "stretch mobility rotation soreness recovery low load"
        )
    if focus == "lower":
        return (
            "upper legs lower legs body weight assisted band quads hamstrings glutes "
            "calves stretch mobility soreness recovery knee low load"
        )
    return (
        "full body body weight assisted band stretch mobility rotation soreness recovery "
        "low load thoracic hips shoulders"
    )


def _mobility_prefer_terms(focus: str) -> list[str]:
    common = ["stretch", "mobility", "assisted", "body weight", "rotation"]
    if focus == "upper":
        return [*common, "shoulder", "scapular", "thoracic", "back", "chest"]
    if focus == "lower":
        return [*common, "quads", "glutes", "hamstrings", "calves", "hips"]
    return [*common, "thoracic", "hips", "shoulders"]


def _mobility_required_terms(focus: str) -> list[str]:
    if focus == "upper":
        return ["stretch", "mobility", "rotation", "shoulder", "scapular", "thoracic"]
    return ["stretch", "mobility", "rotation"]


def _training_query(profile: UserProfile) -> str:
    goal_terms = {
        "fat_loss": "compound strength circuit conditioning squat hinge press row core",
        "hypertrophy": "hypertrophy muscle building press row squat lunge hinge curl extension",
        "strength": "strength compound barbell dumbbell squat hinge press row deadlift",
        "general_fitness": "full body strength conditioning squat hinge press row carry core",
    }
    query = goal_terms.get(profile.goal, goal_terms["general_fitness"])
    equipment = " ".join(profile.equipment_available)
    injuries = " ".join(profile.injury_history)
    return f"{query} {equipment} {injuries}".strip()


def _training_prefer_terms(profile: UserProfile) -> list[str]:
    terms = ["squat", "press", "row", "lunge", "deadlift", "curl", "raise", "pull", "push", "bridge", "plank"]
    if profile.goal == "fat_loss":
        terms.extend(["circuit", "conditioning", "bodyweight"])
    if profile.goal == "strength":
        terms.extend(["barbell", "dumbbell"])
    return terms


def _training_avoid_terms() -> list[str]:
    return [
        "assisted",
        "stretch",
        "mobility",
        "rotation",
        "warm-up",
        "warmup",
        "cooldown",
        "cool-down",
        "flexibility",
    ]


def _fallback_training_hits(profile: UserProfile) -> list[RagHit]:
    allowed = _allowed_exercise_equipment(profile)
    equipment_label = ", ".join(profile.equipment_available) or "bodyweight"
    options = [
        ("Barbell back squat", "Barbell squat pattern for lower-body strength.", "barbell"),
        ("Barbell Romanian deadlift", "Hip hinge pattern for posterior-chain strength.", "barbell"),
        ("Barbell bench press", "Horizontal press pattern for upper-body strength.", "barbell"),
        ("Dumbbell goblet squat", "Dumbbell squat pattern for lower-body volume.", "dumbbell"),
        ("Dumbbell row", "Upper-body pull pattern for back strength.", "dumbbell"),
        ("Dumbbell shoulder press", "Vertical press pattern for shoulders and triceps.", "dumbbell"),
        ("Bodyweight reverse lunge", "Single-leg lower-body pattern using bodyweight.", "body weight"),
        ("Push-up", "Bodyweight horizontal press pattern.", "body weight"),
        ("Plank", "Bodyweight core stability drill.", "body weight"),
    ]
    hits = [
        RagHit(source="exercise_knowledge_base", title=title, snippet=snippet, score=0.82)
        for title, snippet, equipment in options
        if equipment in allowed
    ]
    if hits:
        return hits[:8]
    return [
        RagHit(
            source="exercise_knowledge_base",
            title="Bodyweight full-body circuit",
            snippet=f"Use squat, hinge, push, pull, and core patterns with available equipment: {equipment_label}.",
            score=0.78,
        )
    ]


def _fallback_mobility_hits(focus: str) -> list[RagHit]:
    if focus == "upper":
        return [
            RagHit(
                source="exercise_knowledge_base",
                title="Upper-body mobility reset",
                snippet="Thoracic rotations, wall slides, scapular circles, and pec stretches are low-load options.",
                score=0.88,
            ),
            RagHit(
                source="exercise_knowledge_base",
                title="Shoulder-friendly deload substitutions",
                snippet="Use light band activation and range-of-motion work when upper-body soreness is high.",
                score=0.81,
            ),
        ]
    if focus == "lower":
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
    return [
        RagHit(
            source="exercise_knowledge_base",
            title="Full-body mobility reset",
            snippet="Easy walking, thoracic rotations, hip switches, wall slides, and downshift breathing are low-load options.",
            score=0.86,
        )
    ]


def _allowed_exercise_equipment(profile: UserProfile) -> set[str]:
    normalized = {_normalize_equipment(item) for item in profile.equipment_available}
    allowed = {item for item in normalized if item}
    allowed.update({"body weight", "bodyweight", "assisted"})
    if "dumbbell" in allowed:
        allowed.add("dumbbells")
    if "dumbbells" in allowed:
        allowed.add("dumbbell")
    if "band" in allowed:
        allowed.add("resistance band")
    if "bands" in allowed:
        allowed.update({"band", "resistance band"})
    return allowed


def _equipment_allowed(metadata: dict | None, allowed_equipment: set[str]) -> bool:
    equipment = _normalize_equipment(str((metadata or {}).get("equipment") or ""))
    if not equipment:
        return True
    if equipment in allowed_equipment:
        return True
    if equipment == "dumbbell" and "dumbbells" in allowed_equipment:
        return True
    if equipment == "dumbbells" and "dumbbell" in allowed_equipment:
        return True
    return False


def _normalize_equipment(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _recovery_exercise_avoid_terms() -> list[str]:
    return [
        "deadlift",
        "jump",
        "lunge",
        "press",
        "squat",
        "weighted",
    ]


def _nutrition_prefer_terms(profile: UserProfile) -> list[str]:
    terms = ["protein", "healthy"]
    if profile.goal == "fat_loss":
        terms.extend(["dash", "mediterranean"])
    if profile.goal in {"hypertrophy", "strength"}:
        terms.extend(["protein", "carbs"])
    if any("vegan" in restriction.lower() for restriction in profile.dietary_restrictions):
        terms.append("vegan")
    return terms


def _nutrition_avoid_terms(profile: UserProfile) -> list[str]:
    restrictions = " ".join(profile.dietary_restrictions).lower()
    avoid_terms: list[str] = []
    if "shellfish" in restrictions:
        avoid_terms.extend(["shellfish", "shrimp", "prawn", "crab", "lobster", "scallop"])
    if "dairy" in restrictions:
        avoid_terms.extend(["milk", "cheese", "yogurt", "cream"])
    if "gluten" in restrictions:
        avoid_terms.extend(["wheat", "pasta", "bread"])
    return avoid_terms
