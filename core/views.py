from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .opensearch_client import get_opensearch_client


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

    try:
        size = int(request.GET.get("size", "10"))
    except ValueError:
        size = 10
    size = min(max(size, 1), 50)

    client = get_opensearch_client()

    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "ingredients", "directions", "ner"],
                "fuzziness": "AUTO",
            }
        },
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
            "count": len(results),
            "results": results,
        }
    )