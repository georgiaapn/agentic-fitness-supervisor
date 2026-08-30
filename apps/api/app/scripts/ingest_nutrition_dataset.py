import argparse
import csv
from pathlib import Path
from typing import Any

COLLECTION = "nutrition_knowledge_base"
SOURCE_URI = "kaggle://thedevastator/healthy-diet-recipes-a-comprehensive-dataset/All_Diets.csv"


def ingest_nutrition_dataset(
    db,
    dataset_path: Path,
    *,
    replace: bool = False,
    limit: int | None = None,
) -> int:
    from app.db.models import KnowledgeChunk, KnowledgeDocument

    recipes = _load_dataset(dataset_path)
    if limit is not None:
        recipes = recipes[:limit]

    if replace:
        _delete_existing_collection(db)
    elif _collection_exists(db):
        return 0

    inserted = 0
    for recipe in recipes:
        title = _string(_value(recipe, "Recipe_name", "Recipe Name", "recipe_name"))
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
    name = _string(_value(recipe, "Recipe_name", "Recipe Name", "recipe_name"))
    diet = _string(_value(recipe, "Diet_type", "Diet Type", "diet_type"))
    cuisine = _string(_value(recipe, "Cuisine_type", "Cuisine Type", "cuisine_type"))
    protein = _number(_value(recipe, "Protein(g)", "Protein", "protein"))
    carbs = _number(_value(recipe, "Carbs(g)", "Carbs", "carbohydrates"))
    fat = _number(_value(recipe, "Fat(g)", "Fat", "fat"))
    extraction_day = _string(_value(recipe, "Extraction_day", "Extraction Day", "extraction_day"))

    parts = [
        f"Recipe: {name}.",
        f"Diet type: {diet}." if diet else "",
        f"Cuisine type: {cuisine}." if cuisine else "",
        f"Protein: {protein:g}g." if protein is not None else "",
        f"Carbs: {carbs:g}g." if carbs is not None else "",
        f"Fat: {fat:g}g." if fat is not None else "",
        f"Extraction day: {extraction_day}." if extraction_day else "",
    ]
    return " ".join(part for part in parts if part)


def _metadata_for_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        "diet_type": _string(_value(recipe, "Diet_type", "Diet Type", "diet_type")),
        "cuisine_type": _string(_value(recipe, "Cuisine_type", "Cuisine Type", "cuisine_type")),
        "protein_g": _number(_value(recipe, "Protein(g)", "Protein", "protein")),
        "carbs_g": _number(_value(recipe, "Carbs(g)", "Carbs", "carbohydrates")),
        "fat_g": _number(_value(recipe, "Fat(g)", "Fat", "fat")),
        "extraction_day": _string(_value(recipe, "Extraction_day", "Extraction Day", "extraction_day")),
    }


def _tags_for_recipe(recipe: dict[str, Any]) -> list[str]:
    tags = [
        _value(recipe, "Diet_type", "Diet Type", "diet_type"),
        _value(recipe, "Cuisine_type", "Cuisine Type", "cuisine_type"),
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest recipe CSV data into the RAG knowledge base.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("../../data/raw/nutrition/All_Diets.csv"),
        help="Path to All_Diets.csv from apps/api.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete previously ingested nutrition chunks before inserting.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for quick test ingestion.")
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
        )

    if inserted == 0:
        print("Nutrition dataset already ingested. Use --replace to rebuild it.")
    else:
        print(f"Inserted {inserted} nutrition knowledge chunks into {COLLECTION}.")


if __name__ == "__main__":
    main()
