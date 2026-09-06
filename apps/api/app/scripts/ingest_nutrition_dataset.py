import argparse
import csv
from pathlib import Path
from typing import Any

COLLECTION = "nutrition_knowledge_base"
SOURCE_URI = "local://data/raw/nutrition/healthy_meal_dataset.csv"


def ingest_nutrition_dataset(
    db,
    dataset_path: Path,
    *,
    replace: bool = False,
    limit: int | None = None,
    include_unhealthy: bool = False,
) -> int:
    from app.db.models import KnowledgeChunk, KnowledgeDocument

    recipes = _load_dataset(dataset_path)
    if not include_unhealthy:
        recipes = [recipe for recipe in recipes if _is_healthy(recipe)]
    if limit is not None:
        recipes = recipes[:limit]

    if replace:
        _delete_existing_collection(db)
    elif _collection_exists(db):
        return 0

    inserted = 0
    for recipe in recipes:
        title = _string(_value(recipe, "meal_name", "Recipe_name", "Recipe Name", "recipe_name"))
        if not title:
            continue

        document = KnowledgeDocument(
            collection=COLLECTION,
            title=title[:180],
            source_uri=SOURCE_URI,
            tags={
                "items": _tags_for_recipe(recipe),
                "dataset_row": inserted + 1,
            },
        )
        db.add(document)
        db.flush()

        db.add(
            KnowledgeChunk(
                document_id=document.id,
                collection=COLLECTION,
                title=document.title,
                content=_content_for_recipe(recipe),
                metadata_=_metadata_for_recipe(recipe),
            )
        )
        inserted += 1

    db.commit()
    return inserted


def _load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    return [row for row in rows if row]


def _collection_exists(db) -> bool:
    from sqlalchemy import select

    from app.db.models import KnowledgeDocument

    return (
        db.scalar(
            select(KnowledgeDocument.id)
            .where(KnowledgeDocument.collection == COLLECTION)
            .where(KnowledgeDocument.source_uri == SOURCE_URI)
            .limit(1)
        )
        is not None
    )


def _delete_existing_collection(db) -> None:
    from sqlalchemy import delete, select

    from app.db.models import KnowledgeChunk, KnowledgeDocument

    document_ids = db.scalars(
        select(KnowledgeDocument.id).where(KnowledgeDocument.collection == COLLECTION)
    ).all()
    if not document_ids:
        return

    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(document_ids)))
    db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id.in_(document_ids)))
    db.flush()


def _content_for_recipe(recipe: dict[str, Any]) -> str:
    name = _string(_value(recipe, "meal_name", "Recipe_name", "Recipe Name", "recipe_name"))
    meal_type = _string(_value(recipe, "meal_type"))
    diet = _string(_value(recipe, "diet_type", "Diet_type", "Diet Type"))
    cuisine = _string(_value(recipe, "cuisine", "Cuisine_type", "Cuisine Type"))
    calories = _number(_value(recipe, "calories"))
    protein = _number(_value(recipe, "protein_g", "Protein(g)", "Protein", "protein"))
    carbs = _number(_value(recipe, "carbs_g", "Carbs(g)", "Carbs", "carbohydrates"))
    fat = _number(_value(recipe, "fat_g", "Fat(g)", "Fat", "fat"))
    fiber = _number(_value(recipe, "fiber_g"))
    sugar = _number(_value(recipe, "sugar_g"))
    sodium = _number(_value(recipe, "sodium_mg"))
    cholesterol = _number(_value(recipe, "cholesterol_mg"))
    serving_size = _number(_value(recipe, "serving_size_g"))
    cooking_method = _string(_value(recipe, "cooking_method"))
    prep_time = _number(_value(recipe, "prep_time_min"))
    cook_time = _number(_value(recipe, "cook_time_min"))
    rating = _number(_value(recipe, "rating"))

    parts = [
        f"Meal: {name}.",
        f"Meal type: {meal_type}." if meal_type else "",
        f"Diet type: {diet}." if diet else "",
        f"Cuisine: {cuisine}." if cuisine else "",
        f"Calories: {calories:g} kcal." if calories is not None else "",
        f"Protein: {protein:g}g." if protein is not None else "",
        f"Carbs: {carbs:g}g." if carbs is not None else "",
        f"Fat: {fat:g}g." if fat is not None else "",
        f"Fiber: {fiber:g}g." if fiber is not None else "",
        f"Sugar: {sugar:g}g." if sugar is not None else "",
        f"Sodium: {sodium:g}mg." if sodium is not None else "",
        f"Cholesterol: {cholesterol:g}mg." if cholesterol is not None else "",
        f"Serving size: {serving_size:g}g." if serving_size is not None else "",
        f"Cooking method: {cooking_method}." if cooking_method else "",
        f"Prep time: {prep_time:g} minutes." if prep_time is not None else "",
        f"Cook time: {cook_time:g} minutes." if cook_time is not None else "",
        f"Rating: {rating:g}." if rating is not None else "",
        "Health flag: healthy.",
    ]
    return " ".join(part for part in parts if part)


def _metadata_for_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        "meal_id": _string(_value(recipe, "meal_id")),
        "meal_type": _string(_value(recipe, "meal_type")),
        "diet_type": _string(_value(recipe, "diet_type", "Diet_type", "Diet Type")),
        "cuisine": _string(_value(recipe, "cuisine", "Cuisine_type", "Cuisine Type")),
        "calories": _number(_value(recipe, "calories")),
        "protein_g": _number(_value(recipe, "protein_g", "Protein(g)", "Protein", "protein")),
        "carbs_g": _number(_value(recipe, "carbs_g", "Carbs(g)", "Carbs", "carbohydrates")),
        "fat_g": _number(_value(recipe, "fat_g", "Fat(g)", "Fat", "fat")),
        "fiber_g": _number(_value(recipe, "fiber_g")),
        "sugar_g": _number(_value(recipe, "sugar_g")),
        "sodium_mg": _number(_value(recipe, "sodium_mg")),
        "cholesterol_mg": _number(_value(recipe, "cholesterol_mg")),
        "serving_size_g": _number(_value(recipe, "serving_size_g")),
        "cooking_method": _string(_value(recipe, "cooking_method")),
        "prep_time_min": _number(_value(recipe, "prep_time_min")),
        "cook_time_min": _number(_value(recipe, "cook_time_min")),
        "rating": _number(_value(recipe, "rating")),
        "is_healthy": _is_healthy(recipe),
        "image_url": _string(_value(recipe, "image_url")),
    }


def _tags_for_recipe(recipe: dict[str, Any]) -> list[str]:
    tags = [
        _value(recipe, "meal_type"),
        _value(recipe, "diet_type", "Diet_type", "Diet Type"),
        _value(recipe, "cuisine", "Cuisine_type", "Cuisine Type"),
        _value(recipe, "cooking_method"),
        "healthy" if _is_healthy(recipe) else "",
    ]
    return sorted({str(tag).strip().lower() for tag in tags if str(tag or "").strip()})


def _value(row: dict[str, Any], *keys: str) -> Any:
    normalized = {_normalize_key(key): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(_normalize_key(key))
        if value not in (None, ""):
            return value
    return ""


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _number(value: Any) -> float | None:
    try:
        text = str(value).strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _is_healthy(recipe: dict[str, Any]) -> bool:
    value = _value(recipe, "is_healthy")
    return True if value == "" else _bool(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest recipe CSV data into the RAG knowledge base.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("../../data/raw/nutrition/healthy_meal_dataset.csv"),
        help="Path to healthy_meal_dataset.csv from apps/api.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete previously ingested nutrition chunks before inserting.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for quick test ingestion.")
    parser.add_argument(
        "--include-unhealthy",
        action="store_true",
        help=(
            "Include rows where is_healthy is false. If the dataset has no is_healthy column, "
            "all rows are treated as healthy."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.resolve()

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        inserted = ingest_nutrition_dataset(
            db,
            dataset_path,
            replace=args.replace,
            limit=args.limit,
            include_unhealthy=args.include_unhealthy,
        )

    if inserted == 0:
        print("Nutrition dataset already ingested. Use --replace to rebuild it.")
    else:
        print(f"Inserted {inserted} nutrition knowledge chunks into {COLLECTION}.")


if __name__ == "__main__":
    main()
