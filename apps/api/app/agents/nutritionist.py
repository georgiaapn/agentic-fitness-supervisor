from app.schemas import NutritionPlan, RagHit, SupervisorDirectives, UserProfile
from app.services.rag import RagService


def create_nutrition_plan(
    profile: UserProfile,
    directives: SupervisorDirectives,
    rag: RagService,
) -> NutritionPlan:
    hits = rag.recovery_meals(profile)
    base_calories = int((10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5) * 1.45)
    protein_g = int(profile.weight_kg * 1.8)

    if "lower activity" in directives.nutritionist_directive.lower():
        calorie_target = base_calories - 200
        title = "Recovery-focused nutrition day"
    elif profile.goal == "fat_loss":
        calorie_target = base_calories - 350
        title = "High-satiety fat-loss day"
    else:
        calorie_target = base_calories + 150
        title = "Training-support nutrition day"

    return NutritionPlan(
        title=title,
        calorie_target=calorie_target,
        protein_g=protein_g,
        meals=_meals_from_rag(hits),
        notes=[
            "Keep hydration steady and add electrolytes if morning heart rate remains elevated.",
            "Respect dietary restrictions before final meal selection.",
            "Meal choices are grounded in the retrieved nutrition knowledge base.",
        ],
        rag_context=hits,
    )


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
