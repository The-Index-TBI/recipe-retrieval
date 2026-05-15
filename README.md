# recipe-retrieval
A scalable semantic recipe search engine built with Django and OpenSearch, powered by the RecipeNLG dataset.

## Team

| Name | Student ID | Role |
|------|------------|------|
| Valentino Vieri Zhuo | 2306206446 | OpenSearch Setup & Indexing Pipeline |
| Faust | 2306yyyyyy | Django Backend & Search API |
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