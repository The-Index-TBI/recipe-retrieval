from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .opensearch_client import get_opensearch_client
from .semantic import SemanticSearchUnavailable, encode_query_text


KEYWORD_MAX_RESULT_WINDOW = 10000
SEMANTIC_MAX_RESULT_WINDOW = 1000


def parse_csv_param(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_positive_int(value: str, default: int, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    parsed = max(parsed, 1)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def max_page_for_window(size: int, result_window: int) -> int:
    return max(result_window // size, 1)


def build_ingredient_clauses(ingredients: list[str]) -> list[dict]:
    return [
        {
            "multi_match": {
                "query": ingredient,
                "fields": ["ner^3", "ingredients^2", "title"],
                "type": "phrase",
            }
        }
        for ingredient in ingredients
    ]


def build_keyword_query(
    query: str,
    include_ingredients: list[str],
    exclude_ingredients: list[str],
) -> dict:
    return {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "ingredients", "directions", "ner"],
                        "fuzziness": "AUTO",
                    }
                },
                *build_ingredient_clauses(include_ingredients),
            ],
            "must_not": build_ingredient_clauses(exclude_ingredients),
        }
    }


def build_filter_query(
    include_ingredients: list[str],
    exclude_ingredients: list[str],
) -> dict | None:
    if not include_ingredients and not exclude_ingredients:
        return None

    return {
        "bool": {
            "must": build_ingredient_clauses(include_ingredients),
            "must_not": build_ingredient_clauses(exclude_ingredients),
        }
    }


def extract_total(response: dict) -> tuple[int, str]:
    total = response.get("hits", {}).get("total", {})
    if isinstance(total, dict):
        return total.get("value", 0), total.get("relation", "eq")
    return total, "eq"


def serialize_hits(response: dict) -> list[dict]:
    return [
        {
            "id": hit.get("_id"),
            "score": hit.get("_score"),
            **hit.get("_source", {}),
        }
        for hit in response.get("hits", {}).get("hits", [])
    ]


def pagination_payload(page: int, size: int, total: int, relation: str, max_page: int) -> dict:
    if total <= 0:
        total_pages = 0
    elif relation == "eq":
        total_pages = min(((total - 1) // size) + 1, max_page)
    else:
        total_pages = max_page

    return {
        "page": page,
        "size": size,
        "total": total,
        "total_relation": relation,
        "total_pages": total_pages,
        "max_page": max_page,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


def search_keyword(
    client,
    index_name: str,
    query: str,
    include_ingredients: list[str],
    exclude_ingredients: list[str],
    page: int,
    size: int,
) -> tuple[list[dict], dict]:
    max_page = max_page_for_window(size, KEYWORD_MAX_RESULT_WINDOW)
    page = min(page, max_page)
    offset = (page - 1) * size

    response = client.search(
        index=index_name,
        body={
            "query": build_keyword_query(query, include_ingredients, exclude_ingredients),
            "from": offset,
            "size": size,
        },
    )

    total, relation = extract_total(response)
    return serialize_hits(response), pagination_payload(page, size, total, relation, max_page)


def search_semantic(
    client,
    query: str,
    include_ingredients: list[str],
    exclude_ingredients: list[str],
    page: int,
    size: int,
) -> tuple[list[dict], dict]:
    max_page = max_page_for_window(size, SEMANTIC_MAX_RESULT_WINDOW)
    page = min(page, max_page)
    offset = (page - 1) * size
    k = min(offset + size, SEMANTIC_MAX_RESULT_WINDOW)
    query_vector = encode_query_text(query)

    search_body = {
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": k,
                }
            }
        },
        "from": offset,
        "size": size,
        "track_total_hits": False,
        "_source": {
            "excludes": ["embedding", "search_text"],
        },
    }

    filter_query = build_filter_query(include_ingredients, exclude_ingredients)
    if filter_query:
        search_body["post_filter"] = filter_query

    response = client.search(index=settings.OPENSEARCH_SEMANTIC_INDEX, body=search_body)
    total, relation = extract_total(response)
    return serialize_hits(response), pagination_payload(page, size, total, relation, max_page)


def reciprocal_rank_fusion(keyword_results: list[dict], semantic_results: list[dict]) -> list[dict]:
    ranked: dict[str, dict] = {}
    rank_constant = 60

    for result_set in (keyword_results, semantic_results):
        for rank, result in enumerate(result_set, start=1):
            result_id = result.get("id") or f"{result.get('title', '')}:{result.get('link', '')}"
            if result_id not in ranked:
                ranked[result_id] = {**result, "score": 0.0}
            ranked[result_id]["score"] += 1 / (rank_constant + rank)

    return sorted(ranked.values(), key=lambda item: item.get("score", 0), reverse=True)


def search_hybrid(
    client,
    query: str,
    include_ingredients: list[str],
    exclude_ingredients: list[str],
    page: int,
    size: int,
) -> tuple[list[dict], dict]:
    max_page = max_page_for_window(size, SEMANTIC_MAX_RESULT_WINDOW)
    page = min(page, max_page)
    offset = (page - 1) * size
    rank_window = min(offset + size, SEMANTIC_MAX_RESULT_WINDOW)

    keyword_response = client.search(
        index=settings.OPENSEARCH_SEMANTIC_INDEX,
        body={
            "query": build_keyword_query(query, include_ingredients, exclude_ingredients),
            "size": rank_window,
            "track_total_hits": False,
            "_source": {
                "excludes": ["embedding", "search_text"],
            },
        },
    )

    query_vector = encode_query_text(query)
    semantic_body = {
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": rank_window,
                }
            }
        },
        "size": rank_window,
        "track_total_hits": False,
        "_source": {
            "excludes": ["embedding", "search_text"],
        },
    }
    filter_query = build_filter_query(include_ingredients, exclude_ingredients)
    if filter_query:
        semantic_body["post_filter"] = filter_query

    semantic_response = client.search(index=settings.OPENSEARCH_SEMANTIC_INDEX, body=semantic_body)
    fused_results = reciprocal_rank_fusion(
        serialize_hits(keyword_response),
        serialize_hits(semantic_response),
    )
    page_results = fused_results[offset:offset + size]
    relation = "gte" if len(fused_results) >= rank_window else "eq"
    return page_results, pagination_payload(page, size, len(fused_results), relation, max_page)


@require_GET
def opensearch_health(request):
    client = get_opensearch_client()

    try:
        is_reachable = client.ping()
        index_exists = client.indices.exists(index=settings.OPENSEARCH_INDEX)
    except Exception as exc:
        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
                "index": settings.OPENSEARCH_INDEX,
            },
            status=503,
        )

    status_code = 200 if is_reachable else 503
    return JsonResponse(
        {
            "ok": is_reachable,
            "index": settings.OPENSEARCH_INDEX,
            "index_exists": index_exists,
        },
        status=status_code,
    )


@require_GET
def search_recipes(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse(
            {"error": "Missing query parameter 'q'."},
            status=400,
        )

    mode = request.GET.get("mode", "keyword").strip().lower()
    if mode not in {"keyword", "semantic", "hybrid"}:
        return JsonResponse(
            {"error": "Invalid search mode. Use keyword, semantic, or hybrid."},
            status=400,
        )

    size = parse_positive_int(request.GET.get("size"), default=10, maximum=50)
    page = parse_positive_int(request.GET.get("page"), default=1)
    include_ingredients = parse_csv_param(request.GET.get("include", ""))
    exclude_ingredients = parse_csv_param(request.GET.get("exclude", ""))

    client = get_opensearch_client()

    try:
        if mode == "keyword":
            results, pagination = search_keyword(
                client,
                settings.OPENSEARCH_INDEX,
                query,
                include_ingredients,
                exclude_ingredients,
                page,
                size,
            )
        elif mode == "semantic":
            results, pagination = search_semantic(
                client,
                query,
                include_ingredients,
                exclude_ingredients,
                page,
                size,
            )
        else:
            results, pagination = search_hybrid(
                client,
                query,
                include_ingredients,
                exclude_ingredients,
                page,
                size,
            )
    except SemanticSearchUnavailable as exc:
        return JsonResponse(
            {
                "error": "Semantic search is not available.",
                "details": str(exc),
            },
            status=503,
        )
    except Exception as exc:
        return JsonResponse(
            {
                "error": "Search request failed.",
                "details": str(exc),
            },
            status=503,
        )

    return JsonResponse(
        {
            "query": query,
            "mode": mode,
            "include": include_ingredients,
            "exclude": exclude_ingredients,
            **pagination,
            "count": len(results),
            "results": results,
        }
    )
