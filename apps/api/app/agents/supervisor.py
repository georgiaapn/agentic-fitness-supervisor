from app.schemas import AgentName, RecoveryReport, SupervisorDirectives, UserProfile, WearableSnapshot


def coordinate_day(
    profile: UserProfile,
    wearable: WearableSnapshot,
    recovery: RecoveryReport,
) -> SupervisorDirectives:
    selected: list[AgentName] = ["trainer", "nutritionist"]
    skipped: list[AgentName] = []

    if wearable.pain_level >= 8:
        return SupervisorDirectives(
            selected_agents=["recovery", "nutritionist"],
            skipped_agents=["trainer"],
            trainer_directive="Do not create a training session. Provide safety-first rest guidance only.",
            nutritionist_directive="Create a recovery-supportive eating plan with normal protein.",
            rationale="Pain level is high enough to avoid exercise prescription in the MVP.",
        )

    if recovery.status == "RED":
        trainer_directive = (
            "Replace planned heavy lower-body training with a 30 minute low-load mobility session."
        )
        nutritionist_directive = (
            "Reduce calories slightly for lower activity while keeping protein high and meals recovery-focused."
        )
    elif profile.goal == "fat_loss":
        trainer_directive = "Create a moderate session that preserves lean mass without excessive fatigue."
        nutritionist_directive = "Create a modest calorie deficit with high protein and high satiety meals."
    else:
        trainer_directive = "Create today's planned workout with progressive overload guidance."
        nutritionist_directive = "Create meals that support the user's primary fitness goal."

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
