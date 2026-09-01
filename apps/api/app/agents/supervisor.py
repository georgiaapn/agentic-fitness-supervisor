from app.schemas import (
    AgentName,
    BaselineNutritionDay,
    BaselineWorkoutDay,
    RecoveryReport,
    SupervisorDirectives,
    UserProfile,
    WearableSnapshot,
)


def coordinate_day(
    profile: UserProfile,
    wearable: WearableSnapshot,
    recovery: RecoveryReport,
    *,
    current_day: str | None = None,
    baseline_workout: BaselineWorkoutDay | None = None,
    baseline_nutrition: BaselineNutritionDay | None = None,
) -> SupervisorDirectives:
    selected: list[AgentName] = ["trainer", "nutritionist"]
    skipped: list[AgentName] = []

    if wearable.pain_level >= 8:
        return SupervisorDirectives(
            selected_agents=["trainer", "nutritionist"],
            skipped_agents=[],
            trainer_directive=(
                "Do not prescribe loaded training today. Replace the planned workout with safety-first "
                "rest guidance and a 20 minute low-load full-body mobility session only if movement is pain-free."
            ),
            nutritionist_directive=(
                "Use the saved weekly nutrition baseline as today's starting point, but adjust it for a no-training "
                "recovery day: reduce calories slightly for lower activity, keep protein high, and shift meals toward "
                "recovery-supportive options."
            ),
            rationale="Pain level is high enough to block loaded training while still producing recovery guidance.",
        )

    baseline_conflict = _baseline_recovery_conflict(wearable, baseline_workout)

    if recovery.status == "RED":
        planned_workout = _planned_workout_phrase(baseline_workout)
        replacement_focus = _replacement_focus(baseline_conflict, wearable, baseline_workout)
        trainer_directive = (
            f"Review {planned_workout} for {current_day or 'today'} and replace heavy or fatiguing work "
            f"with a 30 minute low-load {replacement_focus} mobility session."
        )
        planned_nutrition = _planned_nutrition_phrase(baseline_nutrition)
        nutritionist_directive = (
            f"Review {planned_nutrition} and reduce calories slightly for lower activity while keeping "
            "protein high and meals recovery-focused."
        )
    elif baseline_conflict:
        planned_workout = _planned_workout_phrase(baseline_workout)
        trainer_directive = (
            f"Use {planned_workout} as today's baseline, but downshift the session because {baseline_conflict}. "
            "Reduce load and total sets, avoid progressive overload today, and add mobility or easy technique work."
        )
        nutritionist_directive = (
            f"Use {_planned_nutrition_phrase(baseline_nutrition)} as today's baseline and keep protein steady. "
            "Do not reduce calories aggressively because this is a modified training day, not a full rest day."
        )
    elif profile.goal == "fat_loss":
        trainer_directive = (
            f"Use {_planned_workout_phrase(baseline_workout)} as today's baseline and create a moderate "
            "session that preserves lean mass without excessive fatigue."
        )
        nutritionist_directive = (
            f"Use {_planned_nutrition_phrase(baseline_nutrition)} as today's baseline and keep a modest "
            "calorie deficit with high protein and high satiety meals."
        )
    else:
        trainer_directive = (
            f"Use {_planned_workout_phrase(baseline_workout)} as today's baseline and create the planned "
            "workout with progressive overload guidance."
        )
        nutritionist_directive = (
            f"Use {_planned_nutrition_phrase(baseline_nutrition)} as today's baseline and create meals "
            "that support the user's primary fitness goal."
        )

    return SupervisorDirectives(
        selected_agents=selected,
        skipped_agents=skipped,
        trainer_directive=trainer_directive,
        nutritionist_directive=nutritionist_directive,
        rationale=(
            f"User goal is {profile.goal}; recovery status is {recovery.status} "
            f"with readiness {recovery.readiness_score}."
        ),
    )


def _planned_workout_phrase(baseline_workout: BaselineWorkoutDay | None) -> str:
    if baseline_workout is None:
        return "the generated weekly workout plan"
    details = "; ".join(baseline_workout.details[:3])
    if details:
        return f"the saved weekly workout baseline '{baseline_workout.title}' ({details})"
    return f"the saved weekly workout baseline '{baseline_workout.title}'"


def _planned_nutrition_phrase(baseline_nutrition: BaselineNutritionDay | None) -> str:
    if baseline_nutrition is None:
        return "the generated weekly nutrition plan"
    meals = ", ".join(meal.name for meal in baseline_nutrition.meals[:3])
    if meals:
        return f"the saved weekly nutrition baseline '{baseline_nutrition.focus}' ({meals})"
    return f"the saved weekly nutrition baseline '{baseline_nutrition.focus}'"


def _baseline_recovery_conflict(
    wearable: WearableSnapshot,
    baseline_workout: BaselineWorkoutDay | None,
) -> str | None:
    if baseline_workout is None:
        return None

    planned_text = " ".join([baseline_workout.title, *baseline_workout.details]).lower()
    upper_terms = ["upper", "push", "pull", "bench", "press", "row", "chest", "shoulder", "back"]
    lower_terms = ["lower", "legs", "squat", "lunge", "deadlift", "quad", "hamstring", "glute"]

    if wearable.soreness_upper >= 7 and any(term in planned_text for term in upper_terms):
        return "upper-body soreness is high for an upper-body baseline"
    if wearable.soreness_quads >= 7 and any(term in planned_text for term in lower_terms):
        return "quad soreness is high for a lower-body baseline"
    if wearable.pain_level >= 6:
        return "pain level is elevated"
    return None


def _replacement_focus(
    baseline_conflict: str | None,
    wearable: WearableSnapshot,
    baseline_workout: BaselineWorkoutDay | None,
) -> str:
    if baseline_conflict:
        if "upper-body" in baseline_conflict:
            return "upper-body"
        if "lower-body" in baseline_conflict or "quad" in baseline_conflict:
            return "lower-body"

    planned_text = ""
    if baseline_workout is not None:
        planned_text = " ".join([baseline_workout.title, *baseline_workout.details]).lower()

    upper_terms = ["upper", "push", "pull", "bench", "press", "row", "chest", "shoulder", "back"]
    lower_terms = ["lower", "legs", "squat", "lunge", "deadlift", "quad", "hamstring", "glute"]

    if any(term in planned_text for term in upper_terms) and wearable.soreness_upper >= wearable.soreness_quads:
        return "upper-body"
    if any(term in planned_text for term in lower_terms) and wearable.soreness_quads >= wearable.soreness_upper:
        return "lower-body"
    if wearable.soreness_upper >= 7 and wearable.soreness_upper >= wearable.soreness_quads:
        return "upper-body"
    if wearable.soreness_quads >= 7:
        return "lower-body"
    return "full-body"
