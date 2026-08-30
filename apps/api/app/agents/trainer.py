from app.schemas import RagHit, SupervisorDirectives, UserProfile, WearableSnapshot, WorkoutPlan
from app.services.rag import RagService


def create_workout_plan(
    profile: UserProfile,
    wearable: WearableSnapshot,
    directives: SupervisorDirectives,
    rag: RagService,
) -> WorkoutPlan:
    is_mobility_day = "mobility" in directives.trainer_directive.lower()
    hits = rag.mobility_exercises(profile, recovery_safe=is_mobility_day)

    if is_mobility_day:
        selected_blocks = _mobility_blocks_from_rag(hits, wearable.available_minutes)
        return WorkoutPlan(
            title="Lower-body recovery mobility",
            duration_minutes=min(wearable.available_minutes, 30),
            intensity="low",
            blocks=selected_blocks,
            notes=[
                "No heavy squats, lunges, leg press, or deadlifts today.",
                "Keep discomfort below 3 out of 10.",
                "Exercise choices are grounded in the retrieved exercise knowledge base.",
                "Recovery-safe retrieval excludes loaded squat, lunge, jump, press, and deadlift patterns.",
            ],
            rag_context=hits,
        )

    selected_blocks = _training_blocks_from_rag(hits, profile)
    return WorkoutPlan(
        title=f"{profile.goal.replace('_', ' ').title()} training session",
        duration_minutes=wearable.available_minutes,
        intensity="moderate",
        blocks=selected_blocks,
        notes=[
            "Adjust load down if RPE exceeds 8 before the final set.",
            "Exercise choices are grounded in the retrieved exercise knowledge base.",
        ],
        rag_context=hits[:1],
    )


def _mobility_blocks_from_rag(hits: list[RagHit], available_minutes: int) -> list[str]:
    selected = hits[:4]
    if not selected:
        return [
            "5 min nasal-breathing walk or easy bike",
            "2 rounds: cat-cow x 8, 90/90 hip switches x 8 per side",
            "2 rounds: couch stretch 45 sec per side, ankle rocks x 12 per side",
            "3 min downshift breathing",
        ]

    work_minutes = min(available_minutes, 30)
    practice_time = 45 if work_minutes >= 25 else 30
    blocks = ["5 min nasal-breathing walk or easy bike"]
    blocks.extend(
        f"{hit.title}: 2 controlled sets, {practice_time} sec per side or 8-10 slow reps"
        for hit in selected
    )
    blocks.append("3 min downshift breathing")
    return blocks


def _training_blocks_from_rag(hits: list[RagHit], profile: UserProfile) -> list[str]:
    if not hits:
        return [
            "Warm-up: 8 minutes movement prep",
            "Main lift: 3 sets at RPE 7",
            "Accessory superset: 3 rounds",
            "Conditioning finisher: 8 minutes easy to moderate",
        ]

    primary = hits[0].title
    accessory = hits[1].title if len(hits) > 1 else "body-weight accessory pattern"
    volume = "2 sets" if profile.fitness_level == "beginner" else "3 sets"

    return [
        "Warm-up: 8 minutes movement prep",
        f"Primary movement: {primary}, {volume} at RPE 7",
        f"Accessory movement: {accessory}, {volume} with clean tempo",
        "Conditioning finisher: 8 minutes easy to moderate",
    ]
