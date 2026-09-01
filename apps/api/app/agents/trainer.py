import logging

from app.schemas import BaselineWorkoutDay, RagHit, SupervisorDirectives, UserProfile, WearableSnapshot, WorkoutPlan
from app.services.llm import LlmClient
from app.services.rag import RagService

logger = logging.getLogger(__name__)


def create_workout_plan(
    profile: UserProfile,
    wearable: WearableSnapshot,
    directives: SupervisorDirectives,
    rag: RagService,
    llm: LlmClient | None = None,
    baseline_workout: BaselineWorkoutDay | None = None,
    current_day: str | None = None,
) -> WorkoutPlan:
    is_mobility_day = "mobility" in directives.trainer_directive.lower()
    is_downshift_day = "downshift" in directives.trainer_directive.lower() or "reduce load" in directives.trainer_directive.lower()
    recovery_focus = _recovery_focus(wearable, directives, baseline_workout)
    hits = rag.mobility_exercises(profile, recovery_safe=is_mobility_day, focus=recovery_focus)
    if is_mobility_day:
        focused_hits = _focused_mobility_hits(hits, recovery_focus)
        hits = focused_hits if focused_hits or recovery_focus in {"upper", "lower"} else hits

    if is_mobility_day:
        selected_blocks = _mobility_blocks_from_rag(hits, wearable.available_minutes, recovery_focus)
        fallback = WorkoutPlan(
            title=_mobility_title(recovery_focus),
            duration_minutes=min(wearable.available_minutes, 30),
            intensity="low",
            blocks=selected_blocks,
            notes=[
                _baseline_note(baseline_workout, current_day),
                _mobility_safety_note(recovery_focus),
                "Keep discomfort below 3 out of 10.",
                "Exercise choices are grounded in the retrieved exercise knowledge base.",
                "Recovery-safe retrieval excludes heavy loaded patterns that conflict with today's recovery focus.",
            ],
            rag_context=hits,
        )
        return _generate_daily_workout_with_llm(
            profile,
            wearable,
            directives,
            hits,
            fallback,
            llm,
            baseline_workout=baseline_workout,
            current_day=current_day,
        )

    selected_blocks = (
        _downshift_blocks_from_baseline(baseline_workout)
        if is_downshift_day and baseline_workout is not None
        else _training_blocks_from_rag(hits, profile)
    )
    fallback = WorkoutPlan(
        title=(
            f"Modified {baseline_workout.title}"
            if is_downshift_day and baseline_workout is not None
            else baseline_workout.title if baseline_workout is not None else f"{profile.goal.replace('_', ' ').title()} training session"
        ),
        duration_minutes=wearable.available_minutes,
        intensity="low" if is_downshift_day else "moderate",
        blocks=selected_blocks if is_downshift_day else baseline_workout.details if baseline_workout is not None and baseline_workout.details else selected_blocks,
        notes=[
            _baseline_note(baseline_workout, current_day),
            "Downshifted today's baseline because recovery signals conflict with the planned muscle group." if is_downshift_day else "Followed today's baseline plan.",
            "Adjust load down if RPE exceeds 8 before the final set.",
            "Exercise choices are grounded in the retrieved exercise knowledge base.",
        ],
        rag_context=hits[:1],
    )
    return _generate_daily_workout_with_llm(
        profile,
        wearable,
        directives,
        hits,
        fallback,
        llm,
        baseline_workout=baseline_workout,
        current_day=current_day,
    )


def _mobility_blocks_from_rag(hits: list[RagHit], available_minutes: int, focus: str) -> list[str]:
    selected = _focused_mobility_hits(hits, focus)[:4]
    if not selected:
        return _fallback_mobility_blocks(focus)

    work_minutes = min(available_minutes, 30)
    practice_time = 45 if work_minutes >= 25 else 30
    blocks = ["5 min nasal-breathing walk or easy bike"]
    blocks.extend(
        f"{hit.title}: 2 controlled sets, {practice_time} sec per side or 8-10 slow reps"
        for hit in selected
    )
    blocks.append("3 min downshift breathing")
    return blocks


def _fallback_mobility_blocks(focus: str) -> list[str]:
    if focus == "upper":
        return [
            "5 min easy walk with relaxed nasal breathing",
            "2 rounds: thoracic open-book rotations x 8 per side, cat-cow x 8",
            "2 rounds: wall slides x 10, scapular circles x 8 each direction",
            "Doorway pec stretch: 2 x 30 sec per side",
            "3 min downshift breathing",
        ]
    if focus == "lower":
        return [
            "5 min nasal-breathing walk or easy bike",
            "2 rounds: cat-cow x 8, 90/90 hip switches x 8 per side",
            "2 rounds: couch stretch 45 sec per side, ankle rocks x 12 per side",
            "3 min downshift breathing",
        ]
    return [
        "5 min easy walk with relaxed nasal breathing",
        "2 rounds: cat-cow x 8, thoracic rotations x 8 per side",
        "2 rounds: wall slides x 10, 90/90 hip switches x 8 per side",
        "3 min downshift breathing",
    ]


def _focused_mobility_hits(hits: list[RagHit], focus: str) -> list[RagHit]:
    if focus not in {"upper", "lower"}:
        return hits

    focused = [hit for hit in hits if _hit_matches_focus(hit, focus)]
    return focused if focused else []


def _hit_matches_focus(hit: RagHit, focus: str) -> bool:
    haystack = f"{hit.title} {hit.snippet}".lower()
    if focus == "upper":
        upper_terms = ["upper", "shoulder", "chest", "back", "scapular", "thoracic", "neck", "arm"]
        lower_only_terms = ["quad", "calf", "hamstring", "glute", "squat", "lunge", "leg"]
        return any(term in haystack for term in upper_terms) and not any(term in haystack for term in lower_only_terms)

    lower_terms = ["lower", "quad", "calf", "hamstring", "glute", "hip", "ankle", "leg"]
    return any(term in haystack for term in lower_terms)


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


def _recovery_focus(
    wearable: WearableSnapshot,
    directives: SupervisorDirectives,
    baseline_workout: BaselineWorkoutDay | None,
) -> str:
    directive = directives.trainer_directive.lower()
    if "upper-body mobility" in directive or "upper body mobility" in directive:
        return "upper"
    if "lower-body mobility" in directive or "lower body mobility" in directive:
        return "lower"
    if "full-body mobility" in directive or "full body mobility" in directive:
        return "general"

    planned_text = ""
    if baseline_workout is not None:
        planned_text = " ".join([baseline_workout.title, *baseline_workout.details]).lower()

    upper_terms = ["upper", "push", "pull", "bench", "press", "row", "chest", "shoulder", "back"]
    lower_terms = ["lower", "legs", "squat", "lunge", "deadlift", "quad", "hamstring", "glute"]

    if any(term in planned_text for term in upper_terms) and wearable.soreness_upper >= wearable.soreness_quads:
        return "upper"
    if any(term in planned_text for term in lower_terms) and wearable.soreness_quads >= wearable.soreness_upper:
        return "lower"
    if wearable.soreness_upper >= 7 and wearable.soreness_upper >= wearable.soreness_quads:
        return "upper"
    if wearable.soreness_quads >= 7:
        return "lower"
    return "general"


def _mobility_title(focus: str) -> str:
    if focus == "upper":
        return "Upper-body recovery mobility"
    if focus == "lower":
        return "Lower-body recovery mobility"
    return "Recovery mobility reset"


def _mobility_safety_note(focus: str) -> str:
    if focus == "upper":
        return "No heavy pressing, rowing, pulling, or shoulder loading today."
    if focus == "lower":
        return "No heavy squats, lunges, leg press, or deadlifts today."
    return "No heavy loading today; keep the session easy and restorative."


def _downshift_blocks_from_baseline(baseline_workout: BaselineWorkoutDay) -> list[str]:
    adjusted = ["Warm-up: 8 minutes easy mobility and activation"]
    if baseline_workout.details:
        adjusted.extend(f"Technique-only: {detail}, reduce load 20-30% and cut one set" for detail in baseline_workout.details[:3])
    else:
        adjusted.append(f"Technique-only version of {baseline_workout.title}, reduce load 20-30%")
    adjusted.append("Cool-down: 5 minutes gentle stretching and breathing")
    return adjusted


def create_weekly_workout_plan(
    profile: UserProfile,
    rag: RagService,
    llm: LlmClient | None = None,
) -> WorkoutPlan:
    hits = rag.training_exercises(profile)
    exercises = [hit.title for hit in hits[:5]]
    while len(exercises) < 5:
        exercises.append("bodyweight strength circuit")

    goal = profile.goal.replace("_", " ")
    equipment = _available_equipment_text(profile)
    fallback = WorkoutPlan(
        title=f"Weekly {goal} training plan",
        duration_minutes=45,
        intensity="moderate",
        blocks=[
            (
                f"Monday: Lower-body strength - {exercises[0]}: 3 x 8-10 at RPE 7; "
                f"{exercises[1]}: 3 x 8-10; Plank: 3 x 30 sec."
            ),
            (
                f"Tuesday: Upper-body hypertrophy - {exercises[2]}: 3 x 10-12; "
                f"{exercises[3]}: 3 x 10 per side; Push-up: 3 x 8-12."
            ),
            (
                "Wednesday: Zone 2 cardio - Easy bike or incline walk: 30-40 min; "
                "Core plank: 3 x 30 sec; Hip mobility flow: 8 min."
            ),
            (
                f"Thursday: Full-body session - {exercises[0]}: 3 x 8; "
                f"{exercises[4]}: 3 x 10; Dumbbell reverse fly: 3 x 12."
            ),
            (
                f"Friday: Lower-body volume - {exercises[1]}: 3 x 10; "
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
            f"Available equipment:\n{equipment}\n\n"
            f"Retrieved exercise context:\n{_rag_context_json(hits)}\n\n"
            "Requirements:\n"
            "- Include exactly 7 blocks, one for each day from Monday to Sunday.\n"
            "- Format each block as: Day: Session title - exercise or interval; exercise or interval; exercise or interval.\n"
            "- Only prescribe exercises that can be done with the user's available equipment, plus bodyweight movements."
            " Do not include bands, machines, cables, kettlebells, pull-up bars, or other equipment unless listed in the profile.\n"
            "- Monday, Tuesday, Thursday, Friday, and Saturday must be real training days, not stretching-only days.\n"
            "- Every training day must include 3 to 5 specific strength, hypertrophy, conditioning, or core exercises with sets/reps or timed intervals.\n"
            "- Stretching, mobility, and flexibility drills may appear only as warm-up, cool-down, or recovery-day details, not as the main work of a training day.\n"
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
    if _uses_unavailable_equipment(generated, profile):
        logger.info("Trainer weekly plan using deterministic fallback: Gemini used unavailable equipment.")
        return fallback
    if _is_stretching_dominant_week(generated):
        logger.info("Trainer weekly plan using deterministic fallback: Gemini returned a stretching-dominant week.")
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
    baseline_workout: BaselineWorkoutDay | None,
    current_day: str | None,
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
            f"Saved weekly workout baseline for {current_day or 'today'}:\n"
            f"{baseline_workout.model_dump_json() if baseline_workout else 'No saved weekly workout baseline found.'}\n\n"
            f"Retrieved exercise context:\n{_rag_context_json(hits)}\n\n"
            "Requirements:\n"
            "- Treat the saved weekly workout baseline as the starting plan when it exists.\n"
            "- Explain changes through notes, especially if recovery requires replacing the baseline.\n"
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


def _available_equipment_text(profile: UserProfile) -> str:
    if not profile.equipment_available:
        return "bodyweight only"
    return ", ".join(profile.equipment_available)


def _uses_unavailable_equipment(plan: WorkoutPlan, profile: UserProfile) -> bool:
    allowed = {item.strip().lower() for item in profile.equipment_available}
    plan_text = " ".join([plan.title, *plan.blocks, *plan.notes]).lower()
    unavailable_terms = {
        "bands": ["band", "bands", "resistance band"],
        "kettlebell": ["kettlebell", "kettlebells"],
        "cable": ["cable", "cables"],
        "machine": ["machine", "machines"],
        "pull-up bar": ["pull-up bar", "pull up bar", "pullup bar"],
    }

    for equipment, terms in unavailable_terms.items():
        if equipment in allowed:
            continue
        if equipment == "bands" and ("band" in allowed or "resistance band" in allowed):
            continue
        if any(term in plan_text for term in terms):
            return True
    return False


def _is_stretching_dominant_week(plan: WorkoutPlan) -> bool:
    training_terms = [
        "squat",
        "lunge",
        "deadlift",
        "hinge",
        "press",
        "row",
        "push-up",
        "pushup",
        "curl",
        "raise",
        "bridge",
        "plank",
        "carry",
        "circuit",
        "interval",
        "conditioning",
    ]
    recovery_terms = ["stretch", "mobility", "flexibility", "gentle", "recovery", "rest"]

    training_day_count = 0
    recovery_dominant_day_count = 0
    for block in plan.blocks:
        lowered = block.lower()
        has_training = any(term in lowered for term in training_terms)
        recovery_mentions = sum(lowered.count(term) for term in recovery_terms)
        training_mentions = sum(lowered.count(term) for term in training_terms)
        if has_training:
            training_day_count += 1
        if recovery_mentions > training_mentions and not has_training:
            recovery_dominant_day_count += 1

    return training_day_count < 4 or recovery_dominant_day_count > 3


def _baseline_note(baseline_workout: BaselineWorkoutDay | None, current_day: str | None) -> str:
    if baseline_workout is None:
        return "No saved weekly workout baseline was found, so today's session was generated from profile and recovery data."
    return f"Started from the saved {current_day or baseline_workout.day} weekly workout baseline: {baseline_workout.title}."


def _rag_context_json(hits: list[RagHit]) -> str:
    return "[" + ", ".join(hit.model_dump_json() for hit in hits[:6]) + "]"
