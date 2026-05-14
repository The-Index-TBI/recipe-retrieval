import csv
import ast
from opensearchpy import OpenSearch

# Connect to OpenSearch
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    use_ssl=False,
)

# Index name
INDEX_NAME = "recipes"

# Create index if it doesn't exist
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

# Path to your CSV
CSV_PATH = "/mnt/c/Users/USER/Downloads/archive/RecipeNLG_dataset.csv"

# Index first 10,000 recipes
LIMIT = 10000

print(f"Indexing {LIMIT} recipes...")

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= LIMIT:
            break

        doc = {
            "title": row["title"],
            "ingredients": row["ingredients"],
            "directions": row["directions"],
            "link": row["link"],
            "source": row["source"],
            "ner": row["NER"],
        }

        client.index(index=INDEX_NAME, body=doc)

        if i % 1000 == 0:
            print(f"Indexed {i} recipes...")

print("Done!")