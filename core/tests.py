from unittest.mock import MagicMock, patch

from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse


class OpenSearchViewTests(SimpleTestCase):
    def setUp(self):
        self.django_client = Client()
        self.opensearch_client = MagicMock()
        self.opensearch_client.ping.return_value = True
        self.opensearch_client.indices.exists.return_value = True

    @override_settings(OPENSEARCH_INDEX="recipes")
    @patch("core.views.get_opensearch_client")
    def test_opensearch_health_returns_status(self, mock_get_client):
        mock_get_client.return_value = self.opensearch_client

        response = self.django_client.get(reverse("opensearch-health"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            '{"ok": true, "index": "recipes", "index_exists": true}',
        )
        self.opensearch_client.ping.assert_called_once()
        self.opensearch_client.indices.exists.assert_called_once_with(index="recipes")

    @override_settings(OPENSEARCH_INDEX="recipes")
    @patch("core.views.get_opensearch_client")
    def test_opensearch_health_returns_unreachable_status(self, mock_get_client):
        self.opensearch_client.ping.return_value = False
        mock_get_client.return_value = self.opensearch_client

        response = self.django_client.get(reverse("opensearch-health"))

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(
            response.content,
            '{"ok": false, "index": "recipes", "index_exists": true}',
        )

    @override_settings(OPENSEARCH_INDEX="recipes")
    @patch("core.views.get_opensearch_client")
    def test_search_recipes_requires_query(self, mock_get_client):
        mock_get_client.return_value = self.opensearch_client

        response = self.django_client.get(reverse("recipe-search"))

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content,
            '{"error": "Missing query parameter \'q\'."}',
        )
        self.opensearch_client.search.assert_not_called()

    @override_settings(OPENSEARCH_INDEX="recipes")
    @patch("core.views.get_opensearch_client")
    def test_search_recipes_returns_results(self, mock_get_client):
        mock_get_client.return_value = self.opensearch_client
        self.opensearch_client.search.return_value = {
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "hits": [
                    {
                        "_id": "1",
                        "_score": 12.5,
                        "_source": {
                            "title": "Chicken Soup",
                            "ingredients": "chicken, water",
                        },
                    }
                ]
            }
        }

        response = self.django_client.get(reverse("recipe-search"), {"q": "chicken", "size": "3"})

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            '{"query": "chicken", "include": [], "exclude": [], "page": 1, "size": 3, "total": 1, "total_relation": "eq", "count": 1, "results": [{"id": "1", "score": 12.5, "title": "Chicken Soup", "ingredients": "chicken, water"}]}',
        )
        self.opensearch_client.search.assert_called_once()
        called_kwargs = self.opensearch_client.search.call_args.kwargs
        self.assertEqual(called_kwargs["index"], "recipes")
        self.assertEqual(called_kwargs["body"]["size"], 3)
        self.assertEqual(called_kwargs["body"]["from"], 0)
        must_clauses = called_kwargs["body"]["query"]["bool"]["must"]
        self.assertEqual(must_clauses[0]["multi_match"]["query"], "chicken")

    @override_settings(OPENSEARCH_INDEX="recipes")
    @patch("core.views.get_opensearch_client")
    def test_search_recipes_clamps_invalid_size(self, mock_get_client):
        mock_get_client.return_value = self.opensearch_client
        self.opensearch_client.search.return_value = {"hits": {"hits": []}}

        response = self.django_client.get(reverse("recipe-search"), {"q": "chicken", "size": "999"})

        self.assertEqual(response.status_code, 200)
        called_kwargs = self.opensearch_client.search.call_args.kwargs
        self.assertEqual(called_kwargs["body"]["size"], 50)

    @override_settings(OPENSEARCH_INDEX="recipes")
    @patch("core.views.get_opensearch_client")
    def test_search_recipes_supports_ingredient_filters_and_pagination(self, mock_get_client):
        mock_get_client.return_value = self.opensearch_client
        self.opensearch_client.search.return_value = {
            "hits": {
                "total": {"value": 42, "relation": "eq"},
                "hits": [],
            }
        }

        response = self.django_client.get(
            reverse("recipe-search"),
            {
                "q": "chicken",
                "include": "garlic, tomato",
                "exclude": "milk",
                "page": "2",
                "size": "12",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            '{"query": "chicken", "include": ["garlic", "tomato"], "exclude": ["milk"], "page": 2, "size": 12, "total": 42, "total_relation": "eq", "count": 0, "results": []}',
        )

        called_body = self.opensearch_client.search.call_args.kwargs["body"]
        self.assertEqual(called_body["from"], 12)
        self.assertEqual(called_body["size"], 12)

        bool_query = called_body["query"]["bool"]
        self.assertEqual(len(bool_query["must"]), 3)
        self.assertEqual(len(bool_query["must_not"]), 1)
        self.assertEqual(bool_query["must"][1]["multi_match"]["query"], "garlic")
        self.assertEqual(bool_query["must"][2]["multi_match"]["query"], "tomato")
        self.assertEqual(bool_query["must_not"][0]["multi_match"]["query"], "milk")
