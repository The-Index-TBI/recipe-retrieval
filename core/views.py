from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .opensearch_client import get_opensearch_client


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

    size = parse_positive_int(request.GET.get("size"), default=10, maximum=50)
    page = parse_positive_int(request.GET.get("page"), default=1)
    offset = (page - 1) * size
    include_ingredients = parse_csv_param(request.GET.get("include", ""))
    exclude_ingredients = parse_csv_param(request.GET.get("exclude", ""))

    client = get_opensearch_client()

    must_clauses = [
        {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "ingredients", "directions", "ner"],
                "fuzziness": "AUTO",
            }
        }
    ]
    must_not_clauses = []

    for ingredient in include_ingredients:
        must_clauses.append(
            {
                "multi_match": {
                    "query": ingredient,
                    "fields": ["ner^3", "ingredients^2", "title"],
                    "type": "phrase",
                }
            }
        )

    for ingredient in exclude_ingredients:
        must_not_clauses.append(
            {
                "multi_match": {
                    "query": ingredient,
                    "fields": ["ner^3", "ingredients^2", "title"],
                    "type": "phrase",
                }
            }
        )

    search_body = {
        "query": {"bool": {"must": must_clauses, "must_not": must_not_clauses}},
        "from": offset,
        "size": size,
    }

    try:
        response = client.search(index=settings.OPENSEARCH_INDEX, body=search_body)
    except Exception as exc:
        return JsonResponse(
            {
                "error": "Search request failed.",
                "details": str(exc),
            },
            status=503,
        )

    hits = response.get("hits", {}).get("hits", [])
    total = response.get("hits", {}).get("total", {})
    total_value = total.get("value", 0) if isinstance(total, dict) else total
    total_relation = total.get("relation", "eq") if isinstance(total, dict) else "eq"
    results = [
        {
            "id": hit.get("_id"),
            "score": hit.get("_score"),
            **hit.get("_source", {}),
        }
        for hit in hits
    ]

    return JsonResponse(
        {
            "query": query,
            "include": include_ingredients,
            "exclude": exclude_ingredients,
            "page": page,
            "size": size,
            "total": total_value,
            "total_relation": total_relation,
            "count": len(results),
            "results": results,
        }
    )
