"""
Tests for bot.services.api_client. Same httpx.MockTransport approach used
throughout apps/api's own test suite — no real apps/api server or network
access needed. These tests exist to prove the bot's ONLY path to data is
an HTTP call shaped exactly like what apps/api expects (correct path,
correct header for cart identity, correct body for writes) — never a
direct Supabase call or reimplemented business logic.
"""
import httpx

from bot.services import api_client


def _client_with(handler):
    return httpx.Client(base_url="http://test-api", transport=httpx.MockTransport(handler))


def test_list_categories_calls_correct_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/categories"
        return httpx.Response(200, json=[{"id": "c1", "name": "Electronics"}])

    with _client_with(handler) as client:
        result = api_client.list_categories(client)
        assert result[0]["name"] == "Electronics"


def test_get_product_not_found_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    with _client_with(handler) as client:
        result = api_client.get_product(client, "nonexistent")
        assert result is None


def test_get_cart_sends_cart_token_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-cart-token"] == "test-token"
        assert request.url.path == "/cart"
        return httpx.Response(200, json={"cart_id": "c1", "items": [], "subtotal_cents": 0})

    with _client_with(handler) as client:
        result = api_client.get_cart(client, "test-token")
        assert result["subtotal_cents"] == 0


def test_add_to_cart_sends_product_id_and_quantity():
    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        assert body["product_id"] == "prod-1"
        assert body["quantity"] == 1
        assert request.headers["x-cart-token"] == "tok"
        return httpx.Response(201, json={"cart_id": "c1", "items": [], "subtotal_cents": 1999})

    with _client_with(handler) as client:
        result = api_client.add_to_cart(client, "tok", "prod-1")
        assert result["subtotal_cents"] == 1999


def test_create_order_sends_bearer_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer access-token-123"
        assert request.url.path == "/orders"
        return httpx.Response(201, json={"id": "order-1", "status": "pending_payment"})

    with _client_with(handler) as client:
        result = api_client.create_order(client, "access-token-123")
        assert result["id"] == "order-1"


def test_list_orders_sends_bearer_token():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer tok"
        return httpx.Response(200, json=[])

    with _client_with(handler) as client:
        result = api_client.list_orders(client, "tok")
        assert result == []
