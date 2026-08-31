import argparse
import json
from pathlib import Path
from typing import Any

COLLECTION = "recovery_knowledge_base"
SOURCE_URI = "local://data/raw/recovery/recovery_protocols.json"


def ingest_recovery_protocols(
    db,
    dataset_path: Path,
    *,
    replace: bool = False,
    limit: int | None = None,
) -> int:
    from app.db.models import KnowledgeChunk, KnowledgeDocument

    protocols = _load_protocols(dataset_path)
    if limit is not None:
        protocols = protocols[:limit]

    if replace:
        _delete_existing_collection(db)
    elif _collection_exists(db):
        return 0

    inserted = 0
    for protocol in protocols:
        title = _string(protocol.get("title"))
        if not title:
            continue

        document = KnowledgeDocument(
            collection=COLLECTION,
            title=title[:180],
            source_uri=SOURCE_URI,
            tags={
                "items": _string_list(protocol.get("signals")) + _string_list(protocol.get("status")),
                "protocol_id": _string(protocol.get("id")),
            },
        )
        db.add(document)
        db.flush()

        db.add(
            KnowledgeChunk(
                document_id=document.id,
                collection=COLLECTION,
                title=document.title,
                content=_content_for_protocol(protocol),
                metadata_=_metadata_for_protocol(protocol),
            )
        )
        inserted += 1

    db.commit()
    return inserted


def _load_protocols(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Recovery protocol file not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Recovery protocol file must contain a JSON array.")

    return [item for item in data if isinstance(item, dict)]


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


def _content_for_protocol(protocol: dict[str, Any]) -> str:
    parts = [
        f"Protocol: {_string(protocol.get('title'))}.",
        f"Readiness status: {_string(protocol.get('status'))}.",
        _sentence_list("Signals", protocol.get("signals")),
        _sentence_list("Recommended actions", protocol.get("recommended_actions")),
        _sentence_list("Avoid", protocol.get("avoid")),
        f"Escalation: {_string(protocol.get('escalation'))}.",
    ]
    return " ".join(part for part in parts if part and part != "Escalation: .")


def _metadata_for_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": _string(protocol.get("id")),
        "status": _string(protocol.get("status")),
        "signals": _string_list(protocol.get("signals")),
        "recommended_actions": _string_list(protocol.get("recommended_actions")),
        "avoid": _string_list(protocol.get("avoid")),
        "escalation": _string(protocol.get("escalation")),
        "source_urls": _string_list(protocol.get("source_urls")),
    }


def _sentence_list(label: str, value: Any) -> str:
    items = _string_list(value)
    if not items:
        return ""
    return f"{label}: {'; '.join(items)}."


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest recovery protocols into the RAG knowledge base.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("../../data/raw/recovery/recovery_protocols.json"),
        help="Path to recovery_protocols.json from apps/api.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete previously ingested recovery chunks before inserting.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for quick test ingestion.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset.resolve()

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        inserted = ingest_recovery_protocols(
            db,
            dataset_path,
            replace=args.replace,
            limit=args.limit,
        )

    if inserted == 0:
        print("Recovery protocols already ingested. Use --replace to rebuild them.")
    else:
        print(f"Inserted {inserted} recovery knowledge chunks into {COLLECTION}.")


if __name__ == "__main__":
    main()
