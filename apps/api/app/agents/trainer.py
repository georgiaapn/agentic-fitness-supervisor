import logging

from app.schemas import RagHit, SupervisorDirectives, UserProfile, WearableSnapshot, WorkoutPlan
from app.services.llm import LlmClient
from app.services.rag import RagService

logger = logging.getLogger(__name__)


def create_workout_plan(
    profile: UserProfile,
    wearable: WearableSnapshot,
    directives: SupervisorDirectives,
    rag: RagService,
    llm: LlmClient | None = None,
) -> WorkoutPlan:
    is_mobility_day = "mobility" in directives.trainer_directive.lower()
    hits = rag.mobility_exercises(profile, recovery_safe=is_mobility_day)

    if is_mobility_day:
        selected_blocks = _mobility_blocks_from_rag(hits, wearable.available_minutes)
        fallback = WorkoutPlan(
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
        return _generate_daily_workout_with_llm(profile, wearable, directives, hits, fallback, llm)

    selected_blocks = _training_blocks_from_rag(hits, profile)
    fallback = WorkoutPlan(
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
    return _generate_daily_workout_with_llm(profile, wearable, directives, hits, fallback, llm)


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


def create_weekly_workout_plan(
    profile: UserProfile,
    rag: RagService,
    llm: LlmClient | None = None,
) -> WorkoutPlan:
    hits = rag.mobility_exercises(profile)
    exercises = [hit.title for hit in hits[:5]]
    while len(exercises) < 5:
        exercises.append("movement prep circuit")

    goal = profile.goal.replace("_", " ")
    fallback = WorkoutPlan(
        title=f"Weekly {goal} training plan",
        duration_minutes=45,
        intensity="moderate",
        blocks=[
            (
                f"Monday: Lower-body strength - {exercises[0]}: 2 x 30 sec per side; "
                "Goblet squat: 3 x 8-10 at RPE 7; Romanian deadlift: 3 x 8."
            ),
            (
                f"Tuesday: Upper-body hypertrophy - {exercises[1]}: 2 x 30 sec per side; "
                "Dumbbell press: 3 x 10-12; One-arm row: 3 x 10 per side."
            ),
            (
                "Wednesday: Zone 2 cardio - Easy bike or incline walk: 30-40 min; "
                "Core plank: 3 x 30 sec; Hip mobility flow: 8 min."
            ),
            (
                f"Thursday: Full-body session - {exercises[2]}: 2 x 30 sec per side; "
                "Deadlift pattern: 3 x 6 at RPE 7; Band pull-apart: 3 x 15."
            ),
            (
                f"Friday: Lower-body volume - {exercises[3]}: 2 x 30 sec per side; "
                "Split squat variation: 3 x 8 per side; Hamstring curl: 3 x 12."
            ),
            (
                "Saturday: Conditioning and core - Dumbbell circuit: 5 rounds of 40 sec work, 20 sec rest; "
                "Farmer carry: 4 x 30 sec; Easy cooldown walk: 8 min."
            ),
            (
                f"Sunday: Recovery reset - {exercises[4]}: 2 x 45 sec per side; "
                "Nasal-breathing walk: 20 min; Downshift breathing: 5 min."
            ),
        ],
        notes=[
            "Progress load only when all working sets stay at RPE 8 or below.",
            "Use the morning check-in to downshift any heavy day when recovery is RED.",
            "Exercise choices are grounded in the retrieved exercise knowledge base.",
        ],
        rag_context=hits,
    )
    if llm is None or not llm.enabled:
        logger.info("Trainer weekly plan using deterministic fallback: LLM disabled.")
        return fallback

    logger.info("Trainer weekly plan requesting Gemini generation.")
    generated = llm.generate_structured(
        output_model=WorkoutPlan,
        system_prompt=(
            "You are the Trainer Agent in a multi-agent fitness coaching board. "
            "Create practical, safe, beginner-readable training plans. "
            "Use the retrieved exercise context as grounding, respect injury history, "
            "and never claim medical certainty."
        ),
        user_prompt=(
            "Generate a 7-day weekly workout plan as JSON.\n\n"
            f"User profile:\n{profile.model_dump_json()}\n\n"
            f"Retrieved exercise context:\n{_rag_context_json(hits)}\n\n"
            "Requirements:\n"
            "- Include exactly 7 blocks, one for each day from Monday to Sunday.\n"
            "- Format each block as: Day: Session title - exercise or interval; exercise or interval; exercise or interval.\n"
            "- Every training day must include specific exercises with sets/reps or timed intervals.\n"
            "- Rest or recovery days must include a clear recovery prescription such as walking, mobility, stretching, or complete rest.\n"
            "- Keep duration_minutes between 30 and 75.\n"
            "- Use intensity low, moderate, or high.\n"
            "- Include 2 to 5 concise notes.\n"
            "- Omit rag_context or return it as an empty list; the API will attach retrieved context."
        ),
    )
    if generated is None:
        logger.info("Trainer weekly plan using deterministic fallback: Gemini generation failed.")
        return fallback
    logger.info("Trainer weekly plan generated by Gemini.")
    return _with_rag_context(generated, hits)


def _generate_daily_workout_with_llm(
    profile: UserProfile,
    wearable: WearableSnapshot,
    directives: SupervisorDirectives,
    hits: list[RagHit],
    fallback: WorkoutPlan,
    llm: LlmClient | None,
) -> WorkoutPlan:
    if llm is None or not llm.enabled:
        logger.info("Trainer daily plan using deterministic fallback: LLM disabled.")
        return fallback

    logger.info("Trainer daily plan requesting Gemini generation.")
    generated = llm.generate_structured(
        output_model=WorkoutPlan,
        system_prompt=(
            "You are the Trainer Agent in a multi-agent fitness coaching board. "
            "Generate only safe training plans that follow the Supervisor directive. "
            "If recovery constraints require mobility or deloading, do not prescribe heavy loading."
        ),
        user_prompt=(
            "Generate today's workout plan as JSON.\n\n"
            f"User profile:\n{profile.model_dump_json()}\n\n"
            f"Wearable and self-report data:\n{wearable.model_dump_json()}\n\n"
            f"Supervisor directives:\n{directives.model_dump_json()}\n\n"
            f"Retrieved exercise context:\n{_rag_context_json(hits)}\n\n"
            "Requirements:\n"
            "- Keep duration_minutes no higher than available_minutes.\n"
            "- Use intensity low, moderate, or high.\n"
            "- Include 3 to 6 workout blocks.\n"
            "- Include 2 to 5 concise notes.\n"
            "- Omit rag_context or return it as an empty list; the API will attach retrieved context."
        ),
    )
    if generated is None:
        logger.info("Trainer daily plan using deterministic fallback: Gemini generation failed.")
        return fallback
    if "mobility" in directives.trainer_directive.lower() and generated.intensity != "low":
        logger.info(
            "Trainer daily plan using deterministic fallback: Gemini returned non-low intensity for mobility day."
        )
        return fallback
    logger.info("Trainer daily plan generated by Gemini.")
    return _with_rag_context(generated, hits)


def _with_rag_context(plan: WorkoutPlan, hits: list[RagHit]) -> WorkoutPlan:
    notes = list(plan.notes)
    if not any("Gemini" in note for note in notes):
        notes.append("Plan generated by Gemini using retrieved exercise context.")
    return plan.model_copy(update={"rag_context": hits, "notes": notes})


def _rag_context_json(hits: list[RagHit]) -> str:
    return "[" + ", ".join(hit.model_dump_json() for hit in hits[:6]) + "]"
