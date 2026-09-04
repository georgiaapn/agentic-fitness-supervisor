import logging

from app.schemas import (
    NutritionPlan,
    BaselineNutritionDay,
    RagHit,
    SupervisorDirectives,
    UserProfile,
    WeeklyNutritionDay,
    WeeklyNutritionMeal,
    WeeklyNutritionPlan,
)
from app.services.llm import LlmClient
from app.services.rag import RagService

logger = logging.getLogger(__name__)
WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def create_nutrition_plan(
    profile: UserProfile,
    directives: SupervisorDirectives,
    rag: RagService,
    llm: LlmClient | None = None,
    baseline_nutrition: BaselineNutritionDay | None = None,
    current_day: str | None = None,
) -> NutritionPlan:
    hits = rag.recovery_meals(profile)
    base_calories = int((10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5) * 1.45)
    protein_g = int(profile.weight_kg * 1.8)
    directive_text = directives.nutritionist_directive.lower()
    is_recovery_day = any(
        term in directive_text
        for term in ["lower activity", "no-training", "no training", "recovery day", "recovery-supportive"]
    )

    if is_recovery_day:
        calorie_target = base_calories - 200
        title = "Recovery-focused nutrition day"
    elif profile.goal == "fat_loss":
        calorie_target = base_calories - 350
        title = "High-satiety fat-loss day"
    else:
        calorie_target = base_calories + 150
        title = "Training-support nutrition day"

    fallback = NutritionPlan(
        title=title,
        calorie_target=calorie_target,
        protein_g=protein_g,
        meals=_daily_meals(baseline_nutrition, hits, recovery_day=is_recovery_day),
        notes=[
            _baseline_note(baseline_nutrition, current_day),
            (
                "Adjusted today's baseline for lower training demand: keep protein steady, reduce starch portions slightly, "
                "and emphasize produce, omega-3 fats, and hydration."
                if is_recovery_day
                else "Keep hydration steady and add electrolytes if morning heart rate remains elevated."
            ),
            "Respect dietary restrictions before final meal selection.",
            "Meal choices are grounded in the retrieved nutrition knowledge base.",
        ],
        rag_context=hits,
    )
    if llm is None or not llm.enabled:
        logger.info("Nutrition plan using deterministic fallback: LLM disabled.")
        return fallback

    logger.info("Nutrition plan requesting Gemini generation.")
    generated = llm.generate_structured(
        output_model=NutritionPlan,
        system_prompt=(
            "You are the Nutritionist Agent in a multi-agent fitness coaching board. "
            "Create practical nutrition plans grounded in retrieved recipe context. "
            "Respect dietary restrictions and do not provide medical treatment claims."
        ),
        user_prompt=(
            "Generate a nutrition plan as JSON.\n\n"
            f"User profile:\n{profile.model_dump_json()}\n\n"
            f"Supervisor directives:\n{directives.model_dump_json()}\n\n"
            f"Saved weekly nutrition baseline for {current_day or 'today'}:\n"
            f"{baseline_nutrition.model_dump_json() if baseline_nutrition else 'No saved weekly nutrition baseline found.'}\n\n"
            f"Calculated targets:\ncalorie_target={calorie_target}, protein_g={protein_g}\n\n"
            f"Retrieved nutrition context:\n{_rag_context_json(hits)}\n\n"
            "Requirements:\n"
            "- Keep calorie_target within 150 kcal of the calculated target.\n"
            "- Keep protein_g within 15g of the calculated target.\n"
            "- Include 4 meals or meal slots.\n"
            "- Treat the saved weekly nutrition baseline as the starting plan when it exists.\n"
            "- If the Supervisor directive mentions lower activity, no training, or recovery day, do not simply copy the baseline meals."
            " Make a visible adjustment: reduce starchy carb portions slightly, keep protein high, and choose recovery-supportive foods.\n"
            "- Explain changes through notes, especially if recovery or lower activity changes the baseline.\n"
            "- Respect dietary restrictions.\n"
            "- Use retrieved meal_type values as strict slot constraints: Breakfast meals only for Breakfast, "
            "Lunch meals only for Lunch, Dinner meals only for Dinner, and Snack meals only for Snack.\n"
            "- Do not place chicken, fish, beef, pork, pasta bowls, stews, or soups at Breakfast unless the retrieved "
            "context explicitly labels that meal as Breakfast.\n"
            "- Include 2 to 5 concise notes.\n"
            "- Omit rag_context or return it as an empty list; the API will attach retrieved context."
        ),
    )
    if generated is None:
        logger.info("Nutrition plan using deterministic fallback: Gemini generation failed.")
        return fallback
    if abs(generated.calorie_target - calorie_target) > 150:
        logger.info(
            "Nutrition plan using deterministic fallback: Gemini calorie target outside guardrail."
        )
        return fallback
    if abs(generated.protein_g - protein_g) > 15:
        logger.info("Nutrition plan using deterministic fallback: Gemini protein target outside guardrail.")
        return fallback
    if _violates_dietary_restrictions(profile, generated.meals):
        logger.info("Nutrition plan using deterministic fallback: Gemini violated dietary restrictions.")
        return fallback

    logger.info("Nutrition plan generated by Gemini.")
    notes = list(generated.notes)
    if not any("Gemini" in note for note in notes):
        notes.append("Plan generated by Gemini using retrieved nutrition context.")
    return generated.model_copy(update={"rag_context": hits, "notes": notes})


def _daily_meals(
    baseline_nutrition: BaselineNutritionDay | None,
    hits: list[RagHit],
    *,
    recovery_day: bool = False,
) -> list[str]:
    if baseline_nutrition is None or not baseline_nutrition.meals:
        return _meals_from_rag(hits)

    if recovery_day:
        return [
            (
                f"{meal.meal_type}: Adjusted {meal.name} "
                f"({meal.calories} kcal baseline) - keep the protein source, reduce starchy carbs by about 20%, "
                "and add colorful vegetables or fruit."
            )
            for meal in baseline_nutrition.meals
        ]

    return [
        (
            f"{meal.meal_type}: {meal.name} "
            f"({meal.calories} kcal, {meal.protein_g}g protein, {meal.carbs_g}g carbs, {meal.fat_g}g fat)"
        )
        for meal in baseline_nutrition.meals
    ]


def create_weekly_nutrition_plan(
    profile: UserProfile,
    rag: RagService,
    llm: LlmClient | None = None,
) -> WeeklyNutritionPlan:
    hits = rag.recovery_meals(profile)
    daily_calories = _calorie_target_for_goal(profile)
    daily_protein_g = int(profile.weight_kg * 1.8)
    fallback = WeeklyNutritionPlan(
        title=f"Weekly {profile.goal.replace('_', ' ')} nutrition plan",
        daily_calorie_target=daily_calories,
        daily_protein_g=daily_protein_g,
        days=_weekly_days_from_rag(hits, daily_calories, daily_protein_g),
        notes=[
            "Keep meals aligned with the saved profile goal and dietary restrictions.",
            "Distribute protein across the day to support recovery and training adaptation.",
            "Plan generated from retrieved nutrition knowledge with deterministic macro guardrails.",
        ],
        rag_context=hits,
    )
    if llm is None or not llm.enabled:
        logger.info("Nutrition weekly plan using deterministic fallback: LLM disabled.")
        return fallback

    logger.info("Nutrition weekly plan requesting Gemini generation.")
    generated = llm.generate_structured(
        output_model=WeeklyNutritionPlan,
        system_prompt=(
            "You are the Nutritionist Agent in a multi-agent fitness coaching board. "
            "Create a practical 7-day meal plan grounded in retrieved recipe context. "
            "Respect dietary restrictions, match the user's goal, and do not provide medical treatment claims."
        ),
        user_prompt=(
            "Generate a weekly nutrition plan as JSON.\n\n"
            f"User profile:\n{profile.model_dump_json()}\n\n"
            f"Calculated targets:\ndaily_calorie_target={daily_calories}, daily_protein_g={daily_protein_g}\n\n"
            f"Retrieved nutrition context:\n{_rag_context_json(hits)}\n\n"
            "Requirements:\n"
            "- Include exactly 7 days, Monday through Sunday.\n"
            "- Each day must include 4 or 5 meals.\n"
            "- Every meal must include meal_type, name, calories, protein_g, carbs_g, and fat_g.\n"
            "- Keep daily_calorie_target within 150 kcal of the calculated target.\n"
            "- Keep daily_protein_g within 15g of the calculated target.\n"
            "- Respect dietary restrictions from the profile.\n"
            "- Use retrieved meals as grounding where they fit, and treat retrieved meal_type as a strict slot constraint.\n"
            "- Breakfast context may only be used for Breakfast, Lunch context only for Lunch, Dinner context only for Dinner, "
            "and Snack context only for Snack.\n"
            "- Do not place chicken, fish, beef, pork, pasta bowls, stews, or soups at Breakfast unless the retrieved "
            "context explicitly labels that meal as Breakfast.\n"
            "- Include 2 to 5 concise notes.\n"
            "- Omit rag_context or return it as an empty list; the API will attach retrieved context."
        ),
    )
    if generated is None:
        logger.info("Nutrition weekly plan using deterministic fallback: Gemini generation failed.")
        return fallback
    if len(generated.days) != 7 or any(len(day.meals) < 4 or len(day.meals) > 5 for day in generated.days):
        logger.info("Nutrition weekly plan using deterministic fallback: Gemini returned invalid week shape.")
        return fallback
    if abs(generated.daily_calorie_target - daily_calories) > 150:
        logger.info("Nutrition weekly plan using deterministic fallback: Gemini calories outside guardrail.")
        return fallback
    if abs(generated.daily_protein_g - daily_protein_g) > 15:
        logger.info("Nutrition weekly plan using deterministic fallback: Gemini protein outside guardrail.")
        return fallback
    meal_names = [meal.name for day in generated.days for meal in day.meals]
    if _violates_dietary_restrictions(profile, meal_names):
        logger.info("Nutrition weekly plan using deterministic fallback: Gemini violated dietary restrictions.")
        return fallback

    logger.info("Nutrition weekly plan generated by Gemini.")
    notes = list(generated.notes)
    if not any("Gemini" in note for note in notes):
        notes.append("Plan generated by Gemini using retrieved nutrition context.")
    return generated.model_copy(update={"rag_context": hits, "notes": notes})


def _meals_from_rag(hits: list[RagHit]) -> list[str]:
    if not hits:
        return [
            "Greek yogurt bowl with berries, oats, walnuts, and cinnamon",
            "Chicken or tofu grain bowl with leafy greens, olive oil, and legumes",
            "Salmon or lentil dinner with potatoes and roasted vegetables",
            "Optional snack: cottage cheese or hummus with vegetables",
        ]

    meals = [f"{hit.title} ({_macro_summary(hit.snippet)})" for hit in hits[:4]]
    if len(meals) < 4:
        meals.append("Optional snack: cottage cheese or hummus with vegetables")
    return meals


def _weekly_days_from_rag(
    hits: list[RagHit],
    daily_calories: int,
    daily_protein_g: int,
) -> list[WeeklyNutritionDay]:
    meal_templates = _meal_templates(hits)
    days = []
    for index, day in enumerate(WEEK_DAYS):
        rotated = meal_templates[index % len(meal_templates):] + meal_templates[: index % len(meal_templates)]
        days.append(
            WeeklyNutritionDay(
                day=day,
                focus=_day_focus(index),
                meals=_macro_balanced_meals(rotated[:5], daily_calories, daily_protein_g),
            )
        )
    return days


def _meal_templates(hits: list[RagHit]) -> list[str]:
    retrieved = [hit.title for hit in hits[:12] if hit.title]
    fallback = [
        "Greek yogurt bowl with berries and oats",
        "Chicken grain bowl with leafy greens and olive oil",
        "Lentil soup with potatoes and vegetables",
        "Cottage cheese with fruit and walnuts",
        "Tofu rice bowl with vegetables",
        "Turkey wrap with salad and hummus",
        "Egg omelet with whole-grain toast",
    ]
    return retrieved + [meal for meal in fallback if meal not in retrieved]


def _macro_balanced_meals(
    meal_names: list[str],
    daily_calories: int,
    daily_protein_g: int,
) -> list[WeeklyNutritionMeal]:
    meal_types = ["Breakfast", "Lunch", "Snack", "Dinner", "Evening snack"]
    calorie_weights = [0.23, 0.29, 0.13, 0.27, 0.08]
    protein_weights = [0.22, 0.28, 0.14, 0.28, 0.08]
    meals = []
    for index, meal_type in enumerate(meal_types):
        calories = max(120, int(daily_calories * calorie_weights[index]))
        protein = max(8, int(daily_protein_g * protein_weights[index]))
        fat = max(5, int(calories * 0.28 / 9))
        carbs = max(8, int((calories - protein * 4 - fat * 9) / 4))
        meals.append(
            WeeklyNutritionMeal(
                meal_type=meal_type,
                name=meal_names[index % len(meal_names)],
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
            )
        )
    return meals


def _day_focus(index: int) -> str:
    focuses = [
        "Training fuel",
        "Protein distribution",
        "High-satiety meals",
        "Recovery micronutrients",
        "Steady energy",
        "Flexible prep day",
        "Hydration and reset",
    ]
    return focuses[index]


def _calorie_target_for_goal(profile: UserProfile) -> int:
    base_calories = int((10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5) * 1.45)
    if profile.goal == "fat_loss":
        return base_calories - 350
    if profile.goal in {"hypertrophy", "strength"}:
        return base_calories + 150
    return base_calories


def _baseline_note(baseline_nutrition: BaselineNutritionDay | None, current_day: str | None) -> str:
    if baseline_nutrition is None:
        return "No saved weekly nutrition baseline was found, so today's meals were generated from profile and recovery data."
    return f"Started from the saved {current_day or baseline_nutrition.day} weekly nutrition baseline: {baseline_nutrition.focus}."


def _violates_dietary_restrictions(profile: UserProfile, meal_names: list[str]) -> bool:
    restrictions = " ".join(profile.dietary_restrictions).lower()
    if not restrictions:
        return False

    avoid_terms: list[str] = []
    if "shellfish" in restrictions:
        avoid_terms.extend(["shellfish", "shrimp", "prawn", "crab", "lobster", "scallop"])
    if "dairy" in restrictions:
        avoid_terms.extend(["milk", "cheese", "yogurt", "cream"])
    if "gluten" in restrictions:
        avoid_terms.extend(["wheat", "pasta", "bread"])

    haystack = " ".join(meal_names).lower()
    return any(term in haystack for term in avoid_terms)


def _macro_summary(snippet: str) -> str:
    parts = []
    for marker in ["Protein", "Carbs", "Fat"]:
        start = snippet.find(f"{marker}:")
        if start == -1:
            continue
        end = snippet.find(".", start)
        if end == -1:
            end = len(snippet)
        parts.append(snippet[start:end].lower())

    return ", ".join(parts) if parts else "macro details from retrieved recipe"


def _rag_context_json(hits: list[RagHit]) -> str:
    return "[" + ", ".join(hit.model_dump_json() for hit in hits[:6]) + "]"
