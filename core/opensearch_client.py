from functools import lru_cache

from django.conf import settings
from opensearchpy import OpenSearch


@lru_cache(maxsize=1)
def get_opensearch_client() -> OpenSearch:
    http_auth = None
    if settings.OPENSEARCH_USERNAME and settings.OPENSEARCH_PASSWORD:
        http_auth = (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD)

    return OpenSearch(
        hosts=[{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}],
        use_ssl=settings.OPENSEARCH_USE_SSL,
        verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
        http_auth=http_auth,
    )