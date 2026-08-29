from app.schemas import SupervisorDirectives, UserProfile, WearableSnapshot, WorkoutPlan
from app.services.rag import RagService


def create_workout_plan(
    profile: UserProfile,
    wearable: WearableSnapshot,
    directives: SupervisorDirectives,
    rag: RagService,
) -> WorkoutPlan:
    hits = rag.mobility_exercises(profile)

    if "mobility" in directives.trainer_directive.lower():
        return WorkoutPlan(
            title="Lower-body recovery mobility",
            duration_minutes=min(wearable.available_minutes, 30),
            intensity="low",
            blocks=[
                "5 min nasal-breathing walk or easy bike",
                "2 rounds: cat-cow x 8, 90/90 hip switches x 8 per side",
                "2 rounds: couch stretch 45 sec per side, ankle rocks x 12 per side",
                "3 rounds: Spanish squat isometric 20 sec, band pull-aparts x 15",
                "3 min downshift breathing",
            ],
            notes=[
                "No heavy squats, lunges, leg press, or deadlifts today.",
                "Keep discomfort below 3 out of 10.",
            ],
            rag_context=hits,
        )

    return WorkoutPlan(
        title=f"{profile.goal.replace('_', ' ').title()} training session",
        duration_minutes=wearable.available_minutes,
        intensity="moderate",
        blocks=[
            "Warm-up: 8 minutes movement prep",
            "Main lift: 3 sets at RPE 7",
            "Accessory superset: 3 rounds",
            "Conditioning finisher: 8 minutes easy to moderate",
        ],
        notes=["Adjust load down if RPE exceeds 8 before the final set."],
        rag_context=hits[:1],
    )

