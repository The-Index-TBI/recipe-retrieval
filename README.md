# Dishcover
Dishcover is a recipe retrieval project built with Django and OpenSearch on top of the RecipeNLG dataset.

The project focuses on practical cooking intent, not just exact recipe-name lookup. Users can search by ingredients, dish names, or broad cravings, and the app returns ranked recipe results from the indexed corpus.

Live app: https://dishcover-2mlm8.ondigitalocean.app/

## Project Snapshot

This repository currently includes a working Django backend, an OpenSearch indexing pipeline, and a deployed frontend experience. The backend can health-check OpenSearch and run recipe searches against the indexed RecipeNLG corpus, and the frontend renders search results directly from the API.

The longer-term roadmap includes richer filters, semantic retrieval, recipe detail pages, ingredient suggestions, and optional image-assisted search.

## Current Features

- Deployed Django + OpenSearch recipe search app on DigitalOcean.
- Django backend wired to OpenSearch through reusable connection settings.
- OpenSearch health endpoint at `/api/health/opensearch/`.
- Recipe search endpoint at `/api/search/?q=...&include=...&exclude=...&page=...&size=...`.
- OpenSearch indexing script for the RecipeNLG CSV dataset.
- Text search across recipe title, ingredients, directions, and NER fields.
- Boosted title matching in the search query.
- Frontend search UI connected to the backend API.
- Include and exclude ingredient filters for pantry-style search.
- Paginated API and frontend navigation.
- Pagination metadata returns total pages, maximum reachable pages, and next/previous flags.
- Optional semantic search prototype using sentence-transformer embeddings and OpenSearch `knn_vector`.
- Client-side filters for all results, fewer ingredients, simple steps, and many steps.
- Result cards showing score, tags, ingredients, first step preview, and source link.
- Basic Django unit tests for the API surface.
- GitHub Actions workflow that runs the test suite with coverage.
- Codecov-ready coverage output for CI.
- Frontend template and static assets for the initial UI shell.

## Team

| Name | Student ID | Role |
|------|------------|------|
| Valentino Vieri Zhuo | 2306206446 | OpenSearch Setup & Indexing Pipeline |
| Joshua Montolalu | 2306275746 | Django Backend & Search API |
| Henry Aditya Kosasi | 2306214990 | Frontend, Semantic Search & Deployment |

## Dataset

This project uses the [RecipeNLG dataset](https://www.kaggle.com/datasets/paultimothymooney/recipenlg), a large-scale cooking recipe dataset containing over 2.2 million recipes with titles, ingredients, directions, and named entity tags. The dataset was originally created by Poznań University of Technology (PUT) for natural language generation research.

> **Note:** The RecipeNLG dataset is licensed for non-commercial research and educational purposes only. This project is developed strictly as a university course project and is not intended for commercial use. See the full dataset terms [here](https://recipenlg.cs.put.poznan.pl/).

## License

This project's code is provided with no license (all rights reserved). However, any use of this project must comply with the RecipeNLG dataset terms — non-commercial research and educational purposes only.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker on WSL
- [WSL Ubuntu](https://ubuntu.com/desktop/wsl) (optional, but recommended for smoother development)
- Python 3.12+
- Git

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/The-Index-TBI/recipe-retrieval.git
cd recipe-retrieval
```

### 2. Set up virtual environment
```bash
# Make sure your Python version is 3.12 or higher
# Check with: python --version
python -m venv venv
source venv/bin/activate  # Mac/Linux/WSL
venv\Scripts\activate     # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up `.env`
Make a copy of `.env.example` and rename it to `.env`, then fill in the values.

### 5. Pull and run OpenSearch
```bash
docker run -d --name opensearch -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" -e "DISABLE_SECURITY_PLUGIN=true" opensearchproject/opensearch:latest
```

### 6. Verify OpenSearch is running
```bash
curl http://localhost:9200
```

### 7. Download the dataset
Download the RecipeNLG dataset from [Kaggle](https://www.kaggle.com/datasets/paultimothymooney/recipenlg) and place the CSV file somewhere accessible on your machine.

### 8. Index the recipes
```bash
python scripts/index_recipes.py
```

### 9. Test search
```bash
curl -X GET "http://localhost:9200/recipes/_search?pretty" -H "Content-Type: application/json" -d '{
  "query": {
    "multi_match": {
      "query": "sweet and spicy",
      "fields": ["title", "ingredients", "ner"]
    }
  },
  "size": 3
}'
```
Should return 3 ranked recipes. If you see results, everything is working! ✅

### 10. Stop OpenSearch when done
```bash
docker stop opensearch
```

### Running OpenSearch next time
No need to pull the image again. Just start the existing container:
```bash
docker start opensearch
```

## Testing and CI

Run the Django unit tests locally with:

```bash
python manage.py test
```

The repository also includes a GitHub Actions workflow at `.github/workflows/ci.yml` that runs the same test suite with coverage enabled.

For a coverage summary locally, run:

```bash
pip install coverage # if not installed already
python -m coverage run --branch manage.py test
python -m coverage report -m
```

## Planned Features

The following items are planned or partially scoped in the project guide, but are not fully implemented yet:

- Recipe detail endpoint for retrieving a single indexed recipe.
- Ingredient suggestions based on frequent RecipeNLG NER terms.
- Full-corpus semantic indexing and production semantic deployment.
- UI toggle for keyword, semantic, and hybrid retrieval modes.
- Similar recipe search based on vector distance.
- Query understanding for natural language cooking intent.
- Difficulty and time estimates derived from recipe text.
- Search analytics for latency and common query logging.
- Image-assisted search as a stretch feature, not direct image-to-recipe retrieval.

## Architecture Overview

- Django serves the API and the base frontend shell.
- OpenSearch stores the indexed RecipeNLG recipes and powers retrieval.
- `scripts/index_recipes.py` builds the initial index from the CSV dataset.
- The backend currently exposes health and search endpoints; additional endpoints are planned as the project grows.

## API Endpoints

Current backend endpoints:

- `GET /api/health/opensearch/` - checks whether OpenSearch is reachable and whether the target index exists.
- `GET /api/search/?q=...&size=...` - searches recipes with a boosted title match and returns ranked results.
- `GET /api/search/?q=chicken&include=garlic,tomato&exclude=milk&page=2&size=12` - searches recipes with required and excluded ingredient phrases, returning a paginated result page.
- `GET /api/search/?q=quick%20dinner&mode=semantic&size=12` - searches a separately indexed semantic prototype index using OpenSearch k-NN vectors.
- `GET /api/search/?q=quick%20dinner&mode=hybrid&size=12` - combines keyword and semantic prototype results with reciprocal rank fusion.

Planned endpoints include recipe detail, ingredient suggestions, and image-assisted search.

## Semantic Search Prototype

Semantic search is optional and intentionally separate from the main keyword index so the deployed BM25 search remains lightweight.

Install optional dependencies:

```bash
pip install -r requirements-semantic.txt
```

Create a semantic prototype index:

```bash
python scripts/index_semantic_recipes.py
```

Relevant environment variables:

```env
OPENSEARCH_SEMANTIC_INDEX=recipes_semantic
SEMANTIC_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
SEMANTIC_INDEX_LIMIT=10000
SEMANTIC_INDEX_BATCH_SIZE=128
```

Start with a small semantic subset before scaling up. The semantic endpoint expects the semantic index to contain an `embedding` field mapped as an OpenSearch `knn_vector`.
