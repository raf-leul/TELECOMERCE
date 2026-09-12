"""
Tests for app.admin.router. Same httpx.MockTransport pattern as every
other module. The overview test is the most important one — it proves the
Python-side aggregation (order counts by status, revenue calculation
excluding non-revenue statuses, low-stock filtering) actually computes
what it claims, not just that the endpoint returns 200.
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


def test_admin_endpoints_require_auth():
    assert TestClient(app).get("/admin/products").status_code == 401
    assert TestClient(app).get("/admin/orders").status_code == 401
    assert TestClient(app).get("/admin/overview").status_code == 401


def test_admin_endpoints_reject_non_admin(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "11111111-1111-1111-1111-111111111111")

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
        response = TestClient(app).get(
            "/admin/orders", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        rbac_module.service_client = orig
        fake_role_lookup_client.close()


def test_list_all_products_includes_inactive(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "22222222-2222-2222-2222-222222222222")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "admin"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def products_handler(request: httpx.Request) -> httpx.Response:
        # No is_active filter should be present — admin sees everything.
        assert "is_active" not in request.url.params
        return httpx.Response(
            200,
            json=[
                {
                    "id": "p1",
                    "name": "Active",
                    "slug": "active",
                    "description": None,
                    "price_cents": 100,
                    "is_active": True,
                    "category_id": None,
                },
                {
                    "id": "p2",
                    "name": "Draft",
                    "slug": "draft",
                    "description": None,
                    "price_cents": 200,
                    "is_active": False,
                    "category_id": None,
                },
            ],
        )

    fake_products_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(products_handler),
    )

    import app.auth.rbac as rbac_module
    import app.admin.router as admin_router_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_products_client

    app.dependency_overrides[admin_router_module.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).get(
            "/admin/products", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        slugs = {p["slug"] for p in response.json()}
        assert slugs == {"active", "draft"}
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_products_client.close()


def test_overview_aggregates_correctly(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "33333333-3333-3333-3333-333333333333")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "owner"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/rest/v1/orders":
            return httpx.Response(
                200,
                json=[
                    {"status": "paid", "subtotal_cents": 1000},
                    {"status": "paid", "subtotal_cents": 2000},
                    {"status": "pending_payment", "subtotal_cents": 500},
                    {"status": "cancelled", "subtotal_cents": 300},
                    {"status": "delivered", "subtotal_cents": 4000},
                ],
            )
        if path == "/rest/v1/inventory":
            assert request.url.params["quantity_available"] == "lte.5"
            return httpx.Response(
                200,
                json=[
                    {
                        "product_id": "p1",
                        "quantity_available": 2,
                        "products": {"name": "Low Stock Widget"},
                    }
                ],
            )
        raise AssertionError(f"unexpected call: {request.method} {path}")

    fake_data_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    import app.auth.rbac as rbac_module
    import app.admin.router as admin_router_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_data_client

    app.dependency_overrides[admin_router_module.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).get(
            "/admin/overview", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total_orders"] == 5
        # Revenue = paid (1000+2000) + delivered (4000) = 7000.
        # pending_payment and cancelled correctly excluded.
        assert body["revenue_cents"] == 7000
        status_map = {row["status"]: row["count"] for row in body["orders_by_status"]}
        assert status_map == {
            "paid": 2,
            "pending_payment": 1,
            "cancelled": 1,
            "delivered": 1,
        }
        assert len(body["low_stock_products"]) == 1
        assert body["low_stock_products"][0]["product_name"] == "Low Stock Widget"
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_data_client.close()
