import argparse


def embed_knowledge_chunks(
    db,
    *,
    collection: str | None = None,
    limit: int | None = None,
    batch_size: int = 32,
    replace: bool = False,
) -> int:
    from sqlalchemy import select, text

    from app.db.models import KnowledgeChunk
    from app.services.embeddings import embed_documents, vector_literal

    if replace:
        _clear_embeddings(db, collection)

    statement = (
        select(KnowledgeChunk)
        .where(text("embedding IS NULL"))
        .order_by(KnowledgeChunk.created_at.asc())
    )
    if collection:
        statement = statement.where(KnowledgeChunk.collection == collection)
    if limit:
        statement = statement.limit(limit)

    chunks = db.scalars(statement).all()
    embedded = 0

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_documents([_embedding_text(chunk) for chunk in batch])
        for chunk, vector in zip(batch, vectors, strict=True):
            db.execute(
                text(
                    "UPDATE knowledge_chunks "
                    "SET embedding = CAST(:embedding AS vector) "
                    "WHERE id = :chunk_id"
                ),
                {"embedding": vector_literal(vector), "chunk_id": chunk.id},
            )
        db.commit()
        embedded += len(batch)
        print(f"Embedded {embedded}/{len(chunks)} chunks.")

    return embedded


def _clear_embeddings(db, collection: str | None) -> None:
    from sqlalchemy import text

    if collection:
        db.execute(
            text("UPDATE knowledge_chunks SET embedding = NULL WHERE collection = :collection"),
            {"collection": collection},
        )
    else:
        db.execute(text("UPDATE knowledge_chunks SET embedding = NULL"))
    db.commit()


def _embedding_text(chunk) -> str:
    metadata = " ".join(str(value) for value in chunk.metadata_.values())
    return f"{chunk.title}\n{chunk.content}\n{metadata}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate pgvector embeddings for RAG chunks.")
    parser.add_argument(
        "--collection",
        default=None,
        help="Optional knowledge collection to embed, e.g. exercise_knowledge_base.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for a quick smoke test.")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Clear existing embeddings before generating new vectors.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        embedded = embed_knowledge_chunks(
            db,
            collection=args.collection,
            limit=args.limit,
            batch_size=args.batch_size,
            replace=args.replace,
        )

    if embedded == 0:
        print("No chunks needed embeddings.")
    else:
        print(f"Generated embeddings for {embedded} knowledge chunks.")


if __name__ == "__main__":
    main()
