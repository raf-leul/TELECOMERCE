"""
Tests for app.cart.router. Same MockTransport approach as the other test
files — no real network to Supabase.
"""
from datetime import datetime, timedelta, timezone

import httpx
import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import security
from app.cart import router as cart_router
from app.core.config import settings
from app.main import app

GUEST_TOKEN = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _make_token(private_key, sub: str) -> str:
    now = datetime.now(timezone.utc)
    return pyjwt.encode(
        {
            "sub": sub,
            "role": "authenticated",
            "aud": "authenticated",
            "iss": f"{settings.supabase_url}/auth/v1",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


@pytest.fixture(autouse=True)
def _patch_supabase_url(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://test-project.supabase.co")


def _override_service_client(fake_client: httpx.Client):
    def _fake():
        yield fake_client

    app.dependency_overrides[cart_router.get_service_client] = _fake


def test_get_cart_requires_identity():
    response = TestClient(app).get("/cart")
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "MISSING_CART_IDENTITY"


def test_get_cart_rejects_non_uuid_guest_token():
    response = TestClient(app).get(
        "/cart", headers={"X-Cart-Token": "not-a-uuid"}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_CART_TOKEN"


def test_get_cart_creates_guest_cart_and_returns_empty(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, dict(request.url.params)))
        if request.url.path == "/rest/v1/carts" and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path == "/rest/v1/carts" and request.method == "POST":
            return httpx.Response(201, json=[{"id": "cart-1"}])
        if request.url.path == "/rest/v1/cart_items":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected call: {request.method} {request.url}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )
    _override_service_client(fake_client)
    try:
        response = TestClient(app).get(
            "/cart", headers={"X-Cart-Token": GUEST_TOKEN}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["cart_id"] == "cart-1"
        assert body["items"] == []
        assert body["subtotal_cents"] == 0
        # Confirms the guest-cart lookup filtered by guest_token, not user_id.
        get_carts_call = next(c for c in calls if c[1] == "/rest/v1/carts" and c[0] == "GET")
        assert get_carts_call[2]["guest_token"] == f"eq.{GUEST_TOKEN}"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_get_cart_uses_authenticated_user_id(monkeypatch, rsa_keypair):
    private_key, public_key = rsa_keypair

    class FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str):
            return FakeSigningKey(public_key)

    monkeypatch.setattr(security, "get_jwks_client", lambda: FakeJWKSClient())
    user_id = "22222222-2222-2222-2222-222222222222"
    token = _make_token(private_key, user_id)

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, dict(request.url.params)))
        if request.url.path == "/rest/v1/carts" and request.method == "GET":
            return httpx.Response(200, json=[{"id": "cart-2"}])
        if request.url.path == "/rest/v1/cart_items":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected call: {request.method} {request.url}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )
    _override_service_client(fake_client)
    try:
        response = TestClient(app).get(
            "/cart", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["cart_id"] == "cart-2"
        get_carts_call = next(c for c in calls if c[1] == "/rest/v1/carts" and c[0] == "GET")
        assert get_carts_call[2]["user_id"] == f"eq.{user_id}"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_add_item_rejects_inactive_or_missing_product():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/products":
            return httpx.Response(200, json=[])  # no such product
        raise AssertionError("should not reach cart tables if product check fails")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )
    _override_service_client(fake_client)
    try:
        response = TestClient(app).post(
            "/cart/items",
            json={"product_id": "does-not-exist", "quantity": 1},
            headers={"X-Cart-Token": GUEST_TOKEN},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_add_item_computes_server_side_price_not_client_supplied(monkeypatch):
    """
    The request never includes a price at all (CartItemAdd has no price
    field) — this test confirms the response's price genuinely comes from
    the mocked products table lookup, proving there's no path for a client
    to influence pricing.
    """

    # Distinguishes the "check existing line item" GET from the later
    # "_fetch_cart_out" GET, since both hit the same path/method.
    call_count = {"cart_items_get": 0}

    def handler2(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/products":
            return httpx.Response(200, json=[{"id": "p1", "is_active": True}])
        if request.url.path == "/rest/v1/carts":
            return httpx.Response(200, json=[{"id": "cart-3"}])
        if request.url.path == "/rest/v1/cart_items" and request.method == "GET":
            call_count["cart_items_get"] += 1
            if call_count["cart_items_get"] == 1:
                return httpx.Response(200, json=[])  # no existing line item
            return httpx.Response(
                200,
                json=[
                    {
                        "quantity": 2,
                        "product_id": "p1",
                        "products": {
                            "id": "p1",
                            "name": "Widget",
                            "slug": "widget",
                            "price_cents": 500,
                            "is_active": True,
                        },
                    }
                ],
            )
        if request.url.path == "/rest/v1/cart_items" and request.method == "POST":
            return httpx.Response(201, json=[{"id": "ci1"}])
        raise AssertionError(f"unexpected call: {request.method} {request.url}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler2),
    )
    _override_service_client(fake_client)
    try:
        response = TestClient(app).post(
            "/cart/items",
            json={"product_id": "p1", "quantity": 2},
            headers={"X-Cart-Token": GUEST_TOKEN},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["items"][0]["unit_price_cents"] == 500
        assert body["items"][0]["line_total_cents"] == 1000
        assert body["subtotal_cents"] == 1000
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_update_item_not_in_cart_returns_404():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/carts":
            return httpx.Response(200, json=[{"id": "cart-4"}])
        if request.url.path == "/rest/v1/cart_items":
            return httpx.Response(200, json=[])  # PATCH matched no rows
        raise AssertionError(f"unexpected call: {request.method} {request.url}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )
    _override_service_client(fake_client)
    try:
        response = TestClient(app).patch(
            "/cart/items/not-in-cart",
            json={"quantity": 3},
            headers={"X-Cart-Token": GUEST_TOKEN},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_remove_item_not_in_cart_returns_404():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/carts":
            return httpx.Response(200, json=[{"id": "cart-5"}])
        if request.url.path == "/rest/v1/cart_items":
            return httpx.Response(200, json=[])  # DELETE matched no rows
        raise AssertionError(f"unexpected call: {request.method} {request.url}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )
    _override_service_client(fake_client)
    try:
        response = TestClient(app).delete(
            "/cart/items/not-in-cart",
            headers={"X-Cart-Token": GUEST_TOKEN},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        fake_client.close()
