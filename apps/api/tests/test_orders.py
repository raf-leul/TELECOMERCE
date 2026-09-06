"""
Tests for app.orders.router. Same httpx.MockTransport approach as the
other test files — a single handler dispatches on (method, path) to
simulate the multi-step PostgREST calls order creation makes.
"""
from datetime import datetime, timedelta, timezone

import httpx
import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import security
from app.core.config import settings
from app.main import app
from app.orders import router as orders_router


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


@pytest.fixture
def _patch_jwks(monkeypatch, rsa_keypair):
    _private_key, public_key = rsa_keypair

    class FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str):
            return FakeSigningKey(public_key)

    monkeypatch.setattr(security, "get_jwks_client", lambda: FakeJWKSClient())


def test_create_order_requires_auth():
    response = TestClient(app).post("/orders")
    assert response.status_code == 401


def test_create_order_empty_cart_returns_400(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "11111111-1111-1111-1111-111111111111")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/carts":
            return httpx.Response(200, json=[])  # no cart -> empty cart path
        raise AssertionError(f"unexpected call: {request.method} {request.url.path}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[orders_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/orders", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "CART_EMPTY"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_create_order_succeeds_and_snapshots_price_not_client_supplied(
    _patch_jwks, rsa_keypair
):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "22222222-2222-2222-2222-222222222222")

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path

        if path == "/rest/v1/carts":
            return httpx.Response(200, json=[{"id": "cart-1"}])

        if path == "/rest/v1/cart_items" and request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "quantity": 2,
                        "product_id": "prod-1",
                        "products": {
                            "id": "prod-1",
                            "name": "Widget",
                            # authoritative price — must end up in the order,
                            # not anything a client could have sent
                            "price_cents": 1999,
                            "is_active": True,
                        },
                    }
                ],
            )

        if path == "/rest/v1/orders" and request.method == "POST":
            return httpx.Response(
                201,
                json=[
                    {
                        "id": "order-1",
                        "user_id": "22222222-2222-2222-2222-222222222222",
                        "status": "pending_payment",
                        "subtotal_cents": 3998,
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )

        if path == "/rest/v1/order_items" and request.method == "POST":
            body = request.content
            import json as _json

            payload = _json.loads(body)
            assert payload[0]["unit_price_cents"] == 1999
            return httpx.Response(
                201,
                json=[
                    {
                        "product_id": "prod-1",
                        "product_name": "Widget",
                        "unit_price_cents": 1999,
                        "quantity": 2,
                    }
                ],
            )

        if path == "/rest/v1/order_status_history" and request.method == "POST":
            return httpx.Response(201, json=[{}])

        if path == "/rest/v1/cart_items" and request.method == "DELETE":
            return httpx.Response(200, json=[])

        raise AssertionError(f"unexpected call: {request.method} {path}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[orders_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/orders", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["subtotal_cents"] == 3998
        assert body["items"][0]["unit_price_cents"] == 1999
        assert body["items"][0]["line_total_cents"] == 3998
        # Cart was cleared as part of checkout
        assert ("DELETE", "/rest/v1/cart_items") in calls
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_get_order_not_owned_by_user_returns_404(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "33333333-3333-3333-3333-333333333333")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/orders":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "order-2",
                        "user_id": "someone-else",
                        "status": "pending_payment",
                        "subtotal_cents": 100,
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )
        if request.url.path == "/rest/v1/order_items":
            return httpx.Response(200, json=[])
        raise AssertionError("unexpected call")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[orders_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).get(
            "/orders/order-2", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_update_order_status_requires_staff_role(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "44444444-4444-4444-4444-444444444444")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "customer"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    import app.auth.rbac as rbac_module

    orig = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client
    try:
        response = TestClient(app).patch(
            "/orders/order-1/status",
            json={"status": "paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        rbac_module.service_client = orig
        fake_role_lookup_client.close()


def test_update_order_status_invalid_transition_is_409(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "55555555-5555-5555-5555-555555555555")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "admin"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def order_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/orders":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "order-3",
                        "user_id": "someone",
                        "status": "pending_payment",
                        "subtotal_cents": 100,
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )
        if request.url.path == "/rest/v1/order_items":
            return httpx.Response(200, json=[])
        raise AssertionError("unexpected call")

    fake_write_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(order_handler),
    )

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[orders_router.get_service_client] = _fake_service_client
    try:
        # pending_payment -> delivered is not a legal jump
        response = TestClient(app).patch(
            "/orders/order-3/status",
            json={"status": "delivered"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert (
            response.json()["detail"]["error"]["code"] == "INVALID_STATUS_TRANSITION"
        )
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()


def test_update_order_status_valid_transition_succeeds(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "66666666-6666-6666-6666-666666666666")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "owner"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/rest/v1/orders" and request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "order-4",
                        "user_id": "someone",
                        "status": "pending_payment",
                        "subtotal_cents": 100,
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )
        if path == "/rest/v1/orders" and request.method == "PATCH":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "order-4",
                        "user_id": "someone",
                        "status": "paid",
                        "subtotal_cents": 100,
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )
        if path == "/rest/v1/order_status_history":
            return httpx.Response(201, json=[{}])
        if path == "/rest/v1/order_items":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected call: {request.method} {path}")

    fake_write_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[orders_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).patch(
            "/orders/order-4/status",
            json={"status": "paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paid"
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()
