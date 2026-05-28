import ast
import csv
import os
import time

from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError
from sentence_transformers import SentenceTransformer


DEFAULT_LIMIT = 10000
DEFAULT_START_OFFSET = 0
AUTO_START_OFFSET = "auto"
DEFAULT_BATCH_SIZE = 512
DEFAULT_ENCODE_BATCH_SIZE = 128
DEFAULT_REQUEST_TIMEOUT = 120


def env_bool(var_name: str, default: bool = False) -> bool:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def parse_list(value: str):
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value
    return parsed


def as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [str(value)]


def build_recipe_text(title: str, ingredients, directions, ner) -> str:
    ner_text = ", ".join(as_list(ner)[:30])
    ingredients_text = " ".join(as_list(ingredients)[:20])
    directions_text = " ".join(as_list(directions)[:5])
    return f"Title: {title}. Ingredients: {ner_text}. Details: {ingredients_text}. Steps: {directions_text}"


def get_client() -> OpenSearch:
    http_auth = None
    if os.getenv("OPENSEARCH_USERNAME") and os.getenv("OPENSEARCH_PASSWORD"):
        http_auth = (os.getenv("OPENSEARCH_USERNAME"), os.getenv("OPENSEARCH_PASSWORD"))

    return OpenSearch(
        hosts=[
            {
                "host": os.getenv("OPENSEARCH_HOST", "localhost"),
                "port": int(os.getenv("OPENSEARCH_PORT", "9200")),
            }
        ],
        use_ssl=env_bool("OPENSEARCH_USE_SSL", False),
        verify_certs=env_bool("OPENSEARCH_VERIFY_CERTS", False),
        http_auth=http_auth,
        http_compress=True,
        timeout=int(os.getenv("OPENSEARCH_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT))),
        max_retries=3,
        retry_on_timeout=True,
    )


def resolve_device(device: str | None) -> str | None:
    if device != "cuda":
        return device

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "SEMANTIC_DEVICE=cuda requires PyTorch. Install CUDA-enabled PyTorch "
            "inside this virtual environment first."
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError(
            "SEMANTIC_DEVICE=cuda is set, but this virtual environment's PyTorch "
            "was not compiled with CUDA. Run "
            "`python -c \"import torch; print(torch.cuda.is_available()); print(torch.version.cuda)\"` "
            "inside the active venv to confirm, then install a CUDA PyTorch wheel."
        )

    return device


def create_index(client: OpenSearch, index_name: str, dimension: int) -> None:
    if client.indices.exists(index=index_name):
        print(f"Index '{index_name}' already exists.")
        return

    client.indices.create(
        index=index_name,
        body={
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_replicas": 0,
                    "refresh_interval": "-1",
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "ingredients": {"type": "text"},
                    "directions": {"type": "text"},
                    "link": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "ner": {"type": "text"},
                    "search_text": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "space_type": "cosinesimil",
                    },
                }
            },
        },
    )
    print(f"Index '{index_name}' created with {dimension}-dimensional vectors.")


def set_bulk_index_settings(client: OpenSearch, index_name: str) -> None:
    client.indices.put_settings(
        index=index_name,
        body={
            "index": {
                "number_of_replicas": 0,
                "refresh_interval": "-1",
            }
        },
    )


def restore_index_settings(client: OpenSearch, index_name: str) -> None:
    client.indices.put_settings(
        index=index_name,
        body={
            "index": {
                "refresh_interval": "1s",
            }
        },
    )
    client.indices.refresh(index=index_name)


def get_next_semantic_offset(client: OpenSearch, index_name: str) -> int:
    if not client.indices.exists(index=index_name):
        return 0

    client.indices.refresh(index=index_name)
    response = client.count(index=index_name)
    return int(response.get("count", 0))


def bulk_index_documents(
    client: OpenSearch,
    docs: list[dict],
    batch_size: int,
    request_timeout: int,
) -> None:
    helpers.bulk(
        client,
        docs,
        chunk_size=batch_size,
        request_timeout=request_timeout,
        max_retries=3,
        initial_backoff=2,
        max_backoff=30,
    )


def index_batch(
    client: OpenSearch,
    model: SentenceTransformer,
    docs: list[dict],
    texts: list[str],
    batch_size: int,
    encode_batch_size: int,
    request_timeout: int,
) -> tuple[int, float, float, float]:
    encode_started_at = time.perf_counter()
    embeddings = model.encode(
        texts,
        batch_size=encode_batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    encode_seconds = time.perf_counter() - encode_started_at

    for doc, embedding in zip(docs, embeddings):
        doc["_source"]["embedding"] = embedding.tolist()

    bulk_started_at = time.perf_counter()
    bulk_index_documents(client, docs, batch_size, request_timeout)
    bulk_seconds = time.perf_counter() - bulk_started_at

    batch_count = len(docs)
    total_seconds = encode_seconds + bulk_seconds
    rate = batch_count / total_seconds if total_seconds else 0
    return batch_count, encode_seconds, bulk_seconds, rate


def print_batch_progress(
    indexed_count: int,
    csv_row: int,
    encode_seconds: float,
    bulk_seconds: float,
    rate: float,
) -> None:
    print(
        f"Successfully indexed {indexed_count} semantic recipes, "
        f"latest CSV row {csv_row}, encode {encode_seconds:.1f}s, "
        f"bulk {bulk_seconds:.1f}s, rate {rate:.1f}/s..."
    )


def ensure_opensearch_reachable(client: OpenSearch) -> None:
    try:
        client.cluster.health()
    except OpenSearchConnectionError as exc:
        raise RuntimeError(
            "OpenSearch is not reachable. Check the DigitalOcean database status, "
            "trusted sources/network access, host, port, and SSL settings before "
            "running semantic indexing."
        ) from exc


def main() -> None:
    load_dotenv(override=True)

    csv_path = os.getenv("CSV_PATH")
    if not csv_path:
        raise RuntimeError("CSV_PATH is not set. Add it to .env or your shell environment.")

    index_name = os.getenv("OPENSEARCH_SEMANTIC_INDEX", "recipes_semantic")
    model_name = os.getenv("SEMANTIC_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    start_offset_raw = os.getenv("SEMANTIC_START_OFFSET", str(DEFAULT_START_OFFSET)).strip().lower()
    limit = int(os.getenv("SEMANTIC_INDEX_LIMIT", str(DEFAULT_LIMIT)))
    batch_size = int(os.getenv("SEMANTIC_INDEX_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    encode_batch_size = int(os.getenv("SEMANTIC_ENCODE_BATCH_SIZE", str(DEFAULT_ENCODE_BATCH_SIZE)))
    request_timeout = int(os.getenv("OPENSEARCH_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT)))
    device = resolve_device(os.getenv("SEMANTIC_DEVICE") or None)

    client = get_client()
    ensure_opensearch_reachable(client)

    print(f"Loading embedding model '{model_name}'...")
    model = SentenceTransformer(model_name, device=device)
    if hasattr(model, "get_embedding_dimension"):
        dimension = model.get_embedding_dimension()
    else:
        dimension = model.get_sentence_embedding_dimension()
    create_index(client, index_name, dimension)
    set_bulk_index_settings(client, index_name)
    if start_offset_raw == AUTO_START_OFFSET:
        start_offset = get_next_semantic_offset(client, index_name)
        print(f"Auto-resume detected next CSV row {start_offset}.")
    else:
        start_offset = int(start_offset_raw)

    print(
        f"Indexing up to {limit} semantic recipe documents into '{index_name}' "
        f"starting from CSV row {start_offset}..."
    )
    docs = []
    texts = []
    indexed_count = 0
    last_csv_row = start_offset
    completed = False

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i < start_offset:
                    if i > 0 and i % 100000 == 0:
                        print(f"Skipped {i} existing CSV rows...")
                    continue
                if indexed_count >= limit:
                    break

                ingredients = parse_list(row["ingredients"])
                directions = parse_list(row["directions"])
                ner = parse_list(row["NER"])
                search_text = build_recipe_text(row["title"], ingredients, directions, ner)

                docs.append(
                    {
                        "_index": index_name,
                        "_id": str(i),
                        "_source": {
                            "title": row["title"],
                            "ingredients": ingredients,
                            "directions": directions,
                            "link": row["link"],
                            "source": row["source"],
                            "ner": ner,
                            "search_text": search_text,
                        },
                    }
                )
                texts.append(search_text)
                indexed_count += 1
                last_csv_row = i

                if len(docs) >= batch_size:
                    _, encode_seconds, bulk_seconds, rate = index_batch(
                        client,
                        model,
                        docs,
                        texts,
                        batch_size,
                        encode_batch_size,
                        request_timeout,
                    )
                    print_batch_progress(indexed_count, i, encode_seconds, bulk_seconds, rate)
                    docs = []
                    texts = []

        if docs:
            _, encode_seconds, bulk_seconds, rate = index_batch(
                client,
                model,
                docs,
                texts,
                batch_size,
                encode_batch_size,
                request_timeout,
            )
            print(
                f"Indexed the remaining semantic recipes, latest CSV row {last_csv_row}, "
                f"encode {encode_seconds:.1f}s, bulk {bulk_seconds:.1f}s, "
                f"rate {rate:.1f}/s..."
            )
        completed = True
    finally:
        restore_index_settings(client, index_name)

    if completed:
        print("Done! Semantic recipe index is ready.")


if __name__ == "__main__":
    main()
