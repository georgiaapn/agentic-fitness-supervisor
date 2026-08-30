from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk, KnowledgeDocument


SEED_KNOWLEDGE = [
    {
        "collection": "recovery_knowledge_base",
        "title": "Low sleep readiness protocol",
        "tags": ["sleep", "fatigue", "readiness", "deload"],
        "chunks": [
            {
                "title": "Low sleep plus soreness",
                "content": (
                    "When sleep readiness is low and local muscle soreness is high, reduce training "
                    "intensity and avoid heavy loading for the affected muscle group. Favor active "
                    "recovery, easy aerobic work, and mobility until readiness improves."
                ),
                "metadata": {"status": "RED", "constraint": "avoid_heavy_loading"},
            },
            {
                "title": "Elevated resting heart rate",
                "content": (
                    "A resting heart rate above the user's usual baseline can indicate fatigue, stress, "
                    "or poor recovery. Pair this signal with sleep and soreness before changing the plan."
                ),
                "metadata": {"signal": "resting_heart_rate"},
            },
        ],
    },
    {
        "collection": "exercise_knowledge_base",
        "title": "Lower-body mobility reset",
        "tags": ["mobility", "lower_body", "recovery", "knee_friendly"],
        "chunks": [
            {
                "title": "Low-load hip and spine sequence",
                "content": (
                    "Cat-cow, 90/90 hip switches, couch stretch, and ankle rocks are low-load drills "
                    "that restore range of motion without adding meaningful quad fatigue."
                ),
                "metadata": {"equipment": "bodyweight", "duration_minutes": 12},
            },
            {
                "title": "Knee-friendly substitutions",
                "content": (
                    "When knee irritation or quad soreness is present, prefer controlled step-ups, "
                    "Spanish squat isometrics, easy cycling, or band-resisted terminal knee extensions."
                ),
                "metadata": {"contraindication": "knee_irritation"},
            },
        ],
    },
    {
        "collection": "nutrition_knowledge_base",
        "title": "Recovery-focused nutrition",
        "tags": ["protein", "recovery", "anti_inflammatory", "rest_day"],
        "chunks": [
            {
                "title": "Protein distribution on recovery days",
                "content": (
                    "Distribute protein across three to four meals on recovery days. Keep protein high "
                    "even when calories are slightly reduced because tissue repair still requires amino acids."
                ),
                "metadata": {"macro": "protein"},
            },
            {
                "title": "Anti-inflammatory meal pattern",
                "content": (
                    "Recovery-focused meals can include olive oil, berries, leafy greens, legumes, yogurt, "
                    "nuts, and fatty fish or plant omega-3 sources, while respecting user restrictions."
                ),
                "metadata": {"meal_tags": ["omega_3", "produce", "high_protein"]},
            },
        ],
    },
]


def seed_knowledge_base(db: Session) -> None:
    for document_data in SEED_KNOWLEDGE:
        existing = db.scalar(
            select(KnowledgeDocument.id)
            .where(KnowledgeDocument.collection == document_data["collection"])
            .where(KnowledgeDocument.title == document_data["title"])
            .where(KnowledgeDocument.source_uri == "seed://mvp-knowledge-base")
            .limit(1)
        )
        if existing is not None:
            continue

        document = KnowledgeDocument(
            collection=document_data["collection"],
            title=document_data["title"],
            source_uri="seed://mvp-knowledge-base",
            tags={"items": document_data["tags"]},
        )
        db.add(document)
        db.flush()

        for chunk_data in document_data["chunks"]:
            db.add(
                KnowledgeChunk(
                    document_id=document.id,
                    collection=document.collection,
                    title=chunk_data["title"],
                    content=chunk_data["content"],
                    metadata_=chunk_data["metadata"],
                )
            )

    db.commit()
