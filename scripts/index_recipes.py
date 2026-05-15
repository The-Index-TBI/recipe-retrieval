import ast
import csv
import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    use_ssl=False,
)

INDEX_NAME = "recipes"

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

load_dotenv()
CSV_PATH = os.getenv("CSV_PATH")
LIMIT = 10000
BATCH_SIZE = 500

print(f"Indexing {LIMIT} recipes using Bulk method...")

actions = []

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= LIMIT:
            break

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

print("Done! Data siap dicari.")