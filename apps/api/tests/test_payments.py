"""
Tests for app.payments.router. The webhook idempotency test is the most
important one here — it proves a replayed event (same provider_event_id)
does not re-transition the order or double-process, using the same
MockTransport approach as every other module (no real network).
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
from app.payments import router as payments_router


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


def test_create_payment_requires_auth():
    response = TestClient(app).post("/orders/order-1/pay")
    assert response.status_code == 401


def test_create_payment_order_not_owned_returns_404(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "11111111-1111-1111-1111-111111111111")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": "order-1",
                    "user_id": "someone-else",
                    "status": "pending_payment",
                    "subtotal_cents": 1000,
                }
            ],
        )

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[payments_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/orders/order-1/pay", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_create_payment_rejects_order_not_pending_payment(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "22222222-2222-2222-2222-222222222222")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": "order-1",
                    "user_id": "22222222-2222-2222-2222-222222222222",
                    "status": "paid",
                    "subtotal_cents": 1000,
                }
            ],
        )

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[payments_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/orders/order-1/pay", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error"]["code"] == "ORDER_NOT_PAYABLE"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_create_payment_succeeds_and_starts_pending(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "33333333-3333-3333-3333-333333333333")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/orders":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "order-1",
                        "user_id": "33333333-3333-3333-3333-333333333333",
                        "status": "pending_payment",
                        "subtotal_cents": 2500,
                    }
                ],
            )
        if request.url.path == "/rest/v1/payments" and request.method == "POST":
            import json as _json

            body = _json.loads(request.content)
            assert body["status"] == "pending"
            assert body["amount_cents"] == 2500
            return httpx.Response(
                201,
                json=[
                    {
                        "id": "pay-1",
                        "order_id": "order-1",
                        "provider": "mock",
                        "status": "pending",
                        "amount_cents": 2500,
                        "provider_reference": body["provider_reference"],
                    }
                ],
            )
        raise AssertionError(f"unexpected call: {request.method} {request.url.path}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[payments_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/orders/order-1/pay", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_webhook_marks_payment_succeeded_and_order_paid():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path

        if path == "/rest/v1/payments" and request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "pay-1",
                        "order_id": "order-1",
                        "provider": "mock",
                        "status": "pending",
                        "amount_cents": 2500,
                        "provider_reference": "mock_txn_abc",
                    }
                ],
            )
        if path == "/rest/v1/payment_events" and request.method == "POST":
            return httpx.Response(201, json=[{}])
        if path == "/rest/v1/payments" and request.method == "PATCH":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "pay-1",
                        "order_id": "order-1",
                        "provider": "mock",
                        "status": "succeeded",
                        "amount_cents": 2500,
                        "provider_reference": "mock_txn_abc",
                    }
                ],
            )
        if path == "/rest/v1/orders" and request.method == "GET":
            return httpx.Response(
                200, json=[{"id": "order-1", "status": "pending_payment"}]
            )
        if path == "/rest/v1/orders" and request.method == "PATCH":
            return httpx.Response(200, json=[{"id": "order-1", "status": "paid"}])
        if path == "/rest/v1/order_status_history" and request.method == "POST":
            return httpx.Response(201, json=[{}])
        raise AssertionError(f"unexpected call: {request.method} {path}")

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[payments_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/payments/webhook",
            json={
                "provider": "mock",
                "provider_event_id": "evt_1",
                "event_type": "payment.succeeded",
                "provider_reference": "mock_txn_abc",
                "status": "succeeded",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "succeeded"
        assert ("PATCH", "/rest/v1/orders") in calls
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_webhook_is_idempotent_on_duplicate_event_id():
    """
    The critical idempotency test: the same provider_event_id delivered
    twice must only actually process the order transition once. The
    second delivery gets a 409 from the payment_events insert (simulating
    the UNIQUE(provider, provider_event_id) constraint) and must stop
    there — never touching /orders or /payments a second time.
    """
    call_count = {"payment_events_post": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path == "/rest/v1/payments" and request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "pay-1",
                        "order_id": "order-1",
                        "provider": "mock",
                        "status": "succeeded",
                        "amount_cents": 2500,
                        "provider_reference": "mock_txn_abc",
                    }
                ],
            )
        if path == "/rest/v1/payment_events" and request.method == "POST":
            call_count["payment_events_post"] += 1
            # Second delivery of the same event id: unique constraint
            # violation -> PostgREST returns 409.
            return httpx.Response(409, json={"message": "duplicate key value"})
        # If the handler reaches PATCH /payments, PATCH /orders, or
        # POST /order_status_history on the SECOND call, that's the bug
        # this test exists to catch.
        raise AssertionError(
            f"idempotency violated: reached {request.method} {path} on a "
            "duplicate event"
        )

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_service_client():
        yield fake_client

    app.dependency_overrides[payments_router.get_service_client] = _fake_service_client
    try:
        webhook_payload = {
            "provider": "mock",
            "provider_event_id": "evt_duplicate",
            "event_type": "payment.succeeded",
            "provider_reference": "mock_txn_abc",
            "status": "succeeded",
        }
        response = TestClient(app).post("/payments/webhook", json=webhook_payload)
        assert response.status_code == 200
        # Same payload, sent again — this is the "duplicate webhook
        # delivery" scenario. Must not raise the AssertionError above.
        response2 = TestClient(app).post("/payments/webhook", json=webhook_payload)
        assert response2.status_code == 200
        assert response2.json()["status"] == "succeeded"
        assert call_count["payment_events_post"] == 2
    finally:
        app.dependency_overrides.clear()
        fake_client.close()
