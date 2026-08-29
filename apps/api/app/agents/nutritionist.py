from app.schemas import NutritionPlan, SupervisorDirectives, UserProfile
from app.services.rag import RagService


def create_nutrition_plan(
    profile: UserProfile,
    directives: SupervisorDirectives,
    rag: RagService,
) -> NutritionPlan:
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
        meals=[
            "Greek yogurt bowl with berries, oats, walnuts, and cinnamon",
            "Chicken or tofu grain bowl with leafy greens, olive oil, and legumes",
            "Salmon or lentil dinner with potatoes and roasted vegetables",
            "Optional snack: cottage cheese or hummus with vegetables",
        ],
        notes=[
            "Keep hydration steady and add electrolytes if morning heart rate remains elevated.",
            "Respect dietary restrictions before final meal selection.",
        ],
        rag_context=rag.recovery_meals(profile),
    )

