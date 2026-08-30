from functools import lru_cache

from app.config import settings


class EmbeddingProviderUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingProviderUnavailable(
            'Install RAG extras with: pip install -e ".[rag]"'
        ) from exc

    try:
        return SentenceTransformer(settings.embedding_model)
    except Exception as exc:
        raise EmbeddingProviderUnavailable(
            f"Could not load embedding model: {settings.embedding_model}"
        ) from exc


def embed_query(text: str) -> list[float]:
    return _embed([f"query: {text}"])[0]


def embed_documents(texts: list[str]) -> list[list[float]]:
    return _embed([f"passage: {text}" for text in texts])


def _embed(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [embedding.astype(float).tolist() for embedding in embeddings]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
