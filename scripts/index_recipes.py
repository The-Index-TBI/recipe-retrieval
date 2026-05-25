import ast
import csv
import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers

INDEX_NAME = "recipes"
DEFAULT_LIMIT = 10000
DEFAULT_BATCH_SIZE = 500


def env_bool(var_name: str, default: bool = False) -> bool:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


load_dotenv(override=True)

http_auth = None
if os.getenv("OPENSEARCH_USERNAME") and os.getenv("OPENSEARCH_PASSWORD"):
    http_auth = (os.getenv("OPENSEARCH_USERNAME"), os.getenv("OPENSEARCH_PASSWORD"))

client = OpenSearch(
    hosts=[
        {
            "host": os.getenv("OPENSEARCH_HOST", "localhost"),
            "port": int(os.getenv("OPENSEARCH_PORT", "9200")),
        }
    ],
    use_ssl=env_bool("OPENSEARCH_USE_SSL", False),
    verify_certs=env_bool("OPENSEARCH_VERIFY_CERTS", False),
    http_auth=http_auth,
)

CSV_PATH = os.getenv("CSV_PATH")
LIMIT = int(os.getenv("INDEX_LIMIT", str(DEFAULT_LIMIT)))
BATCH_SIZE = int(os.getenv("INDEX_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))

if not CSV_PATH:
    raise RuntimeError("CSV_PATH is not set. Add it to .env or your shell environment.")

# Create index mapping
if not client.indices.exists(index=INDEX_NAME):
    client.indices.create(index=INDEX_NAME, body={
        "mappings": {
            "properties": {
                "title": {"type": "text"},
                "ingredients": {"type": "text"},
                "directions": {"type": "text"},
                "link": {"type": "keyword"},
                "source": {"type": "keyword"},
                "ner": {"type": "text"},
            }
        }
    })
    print(f"Index '{INDEX_NAME}' created.")

print(f"Indexing {LIMIT} recipes using Bulk method...")

actions = []

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        # Ubah string dari CSV menjadi Array/List Python
        # agar OpenSearch lebih mudah melakukan pencarian (keyword matching)
        try:
            ingredients_list = ast.literal_eval(row["ingredients"])
            directions_list = ast.literal_eval(row["directions"])
            ner_list = ast.literal_eval(row["NER"])
        except (ValueError, SyntaxError):
            # Jika gagal di-parse, kembalikan ke bentuk string asli
            ingredients_list = row["ingredients"]
            directions_list = row["directions"]
            ner_list = row["NER"]

        doc = {
            "_index": INDEX_NAME,
            "_source": {
                "title": row["title"],
                "ingredients": ingredients_list,
                "directions": directions_list,
                "link": row["link"],
                "source": row["source"],
                "ner": ner_list,
            }
        }
        actions.append(doc)

        if len(actions) >= BATCH_SIZE:
            helpers.bulk(client, actions)
            actions = []
            print(f"Successfully indexed {i + 1} recipes...")

if len(actions) > 0:
    helpers.bulk(client, actions)
    print("Indexed the remaining recipes...")

print("Done! Data is ready to be searched.")
