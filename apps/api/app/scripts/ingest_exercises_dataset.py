import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk, KnowledgeDocument
from app.db.session import SessionLocal

COLLECTION = "exercise_knowledge_base"
SOURCE_URI = "github://hasaneyldrm/exercises-dataset/data/exercises.json"


def ingest_exercises_dataset(
    db: Session,
    dataset_path: Path,
    *,
    replace: bool = False,
    limit: int | None = None,
) -> int:
    exercises = _load_dataset(dataset_path)
    if limit is not None:
        exercises = exercises[:limit]

    if replace:
        _delete_existing_collection(db)
    elif _collection_exists(db):
        return 0

    inserted = 0
    for exercise in exercises:
        document = KnowledgeDocument(
            collection=COLLECTION,
            title=_string(exercise.get("name"), fallback="Unnamed exercise"),
            source_uri=SOURCE_URI,
            tags={
                "items": _tags_for_exercise(exercise),
                "dataset_id": exercise.get("id"),
            },
        )
        db.add(document)
        db.flush()

        db.add(
            KnowledgeChunk(
                document_id=document.id,
                collection=COLLECTION,
                title=document.title,
                content=_content_for_exercise(exercise),
                metadata_=_metadata_for_exercise(exercise),
            )
        )
        inserted += 1

    db.commit()
    return inserted


def _load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected exercises dataset to be a JSON array.")

    return [item for item in data if isinstance(item, dict)]


def _collection_exists(db: Session) -> bool:
    return (
        db.scalar(
            select(KnowledgeDocument.id)
            .where(KnowledgeDocument.collection == COLLECTION)
            .where(KnowledgeDocument.source_uri == SOURCE_URI)
            .limit(1)
        )
        is not None
    )


def _delete_existing_collection(db: Session) -> None:
    document_ids = db.scalars(
        select(KnowledgeDocument.id)
        .where(KnowledgeDocument.collection == COLLECTION)
    ).all()
    if not document_ids:
        return

    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(document_ids)))
    db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id.in_(document_ids)))
    db.flush()


def _content_for_exercise(exercise: dict[str, Any]) -> str:
    name = _string(exercise.get("name"), fallback="Unnamed exercise")
    category = _string(exercise.get("category"))
    body_part = _string(exercise.get("body_part"))
    equipment = _string(exercise.get("equipment"))
    target = _string(exercise.get("target"))
    muscle_group = _string(exercise.get("muscle_group"))
    secondary_muscles = ", ".join(_string_list(exercise.get("secondary_muscles")))
    instructions = _english_instruction_text(exercise)

    parts = [
        f"Exercise: {name}.",
        f"Category: {category}." if category else "",
        f"Body part: {body_part}." if body_part else "",
        f"Equipment: {equipment}." if equipment else "",
        f"Target: {target}." if target else "",
        f"Muscle group: {muscle_group}." if muscle_group else "",
        f"Secondary muscles: {secondary_muscles}." if secondary_muscles else "",
        f"Instructions: {instructions}" if instructions else "",
    ]
    return " ".join(part for part in parts if part)


def _metadata_for_exercise(exercise: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": exercise.get("id"),
        "category": exercise.get("category"),
        "body_part": exercise.get("body_part"),
        "equipment": exercise.get("equipment"),
        "target": exercise.get("target"),
        "muscle_group": exercise.get("muscle_group"),
        "secondary_muscles": _string_list(exercise.get("secondary_muscles")),
        "image_ref": exercise.get("image"),
        "gif_ref": exercise.get("gif_url"),
        "media_id": exercise.get("media_id"),
        "attribution": exercise.get("attribution"),
    }


def _tags_for_exercise(exercise: dict[str, Any]) -> list[str]:
    tags = [
        exercise.get("category"),
        exercise.get("body_part"),
        exercise.get("equipment"),
        exercise.get("target"),
        exercise.get("muscle_group"),
        *_string_list(exercise.get("secondary_muscles")),
    ]
    return sorted({str(tag).strip().lower() for tag in tags if str(tag or "").strip()})


def _english_instruction_text(exercise: dict[str, Any]) -> str:
    instruction_steps = exercise.get("instruction_steps")
    if isinstance(instruction_steps, dict):
        steps = instruction_steps.get("en")
        if isinstance(steps, list):
            return " ".join(_string_list(steps))

    instructions = exercise.get("instructions")
    if isinstance(instructions, dict):
        value = instructions.get("en")
        if isinstance(value, list):
            return " ".join(_string_list(value))
        return _string(value)

    if isinstance(instructions, list):
        return " ".join(_string_list(instructions))

    return _string(instructions)


def _string(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest exercise JSON into the RAG knowledge base.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("../../data/raw/exercises/exercises.json"),
        help="Path to exercises.json from apps/api.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete previously ingested exercise dataset chunks before inserting.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for quick test ingestion.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.resolve()

    with SessionLocal() as db:
        inserted = ingest_exercises_dataset(
            db,
            dataset_path,
            replace=args.replace,
            limit=args.limit,
        )

    if inserted == 0:
        print("Exercise dataset already ingested. Use --replace to rebuild it.")
    else:
        print(f"Inserted {inserted} exercise knowledge chunks into {COLLECTION}.")


if __name__ == "__main__":
    main()
