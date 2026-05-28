from functools import lru_cache

from django.conf import settings


class SemanticSearchUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SemanticSearchUnavailable(
            "Install optional semantic dependencies with "
            "`pip install -r requirements-semantic.txt`."
        ) from exc

    return SentenceTransformer(settings.SEMANTIC_MODEL_NAME)


def encode_query_text(query: str) -> list[float]:
    model = get_embedding_model()
    embedding = model.encode(query, normalize_embeddings=True)
    return embedding.tolist()
