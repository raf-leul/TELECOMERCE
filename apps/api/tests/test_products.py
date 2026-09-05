"""
Tests for app.products.router. Supabase/PostgREST calls are never made for
real here — httpx.MockTransport intercepts every request, so these tests
exercise the actual routing/serialization/RBAC logic without needing
network access to Supabase (which this sandbox's egress doesn't allow
anyway — see docs/DECISIONS.md).
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
from app.products import router as products_router


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


def test_list_products_returns_only_what_postgrest_returns(monkeypatch):
    """
    Confirms the endpoint doesn't add its own filtering logic that could
    mask an RLS misconfiguration — it must return exactly what the anon
    PostgREST call returns, because RLS (not this code) is what's
    responsible for hiding inactive products (see Stage 2 verification in
    docs/DATABASE.md).
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/products"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "p1",
                    "name": "Active Widget",
                    "slug": "active-widget",
                    "description": None,
                    "price_cents": 1999,
                    "is_active": True,
                    "category_id": None,
                }
            ],
        )

    fake_client = httpx.Client(base_url="https://test-project.supabase.co/rest/v1", transport=httpx.MockTransport(handler))
    def _fake_anon_client():
        yield fake_client

    app.dependency_overrides[products_router.get_anon_client] = _fake_anon_client
    try:
        client = TestClient(app)
        response = client.get("/products")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["slug"] == "active-widget"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_list_products_backend_error_is_translated_not_leaked():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="raw postgres internals, should not leak")

    fake_client = httpx.Client(base_url="https://test-project.supabase.co/rest/v1", transport=httpx.MockTransport(handler))
    def _fake_anon_client():
        yield fake_client

    app.dependency_overrides[products_router.get_anon_client] = _fake_anon_client
    try:
        client = TestClient(app)
        response = client.get("/products")
        assert response.status_code == 502
        assert "raw postgres internals" not in response.text
        assert response.json()["detail"]["error"]["code"] == "CATALOG_BACKEND_ERROR"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_create_product_requires_auth():
    response = TestClient(app).post(
        "/products",
        json={"name": "x", "slug": "x", "price_cents": 100},
    )
    assert response.status_code == 401


def test_create_product_requires_admin_role(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "33333333-3333-3333-3333-333333333333")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/profiles"
        return httpx.Response(200, json=[{"role": "customer"}])

    fake_service_client = httpx.Client(base_url="https://test-project.supabase.co/rest/v1", transport=httpx.MockTransport(profile_handler))

    def fake_service_client_ctx():
        return fake_service_client

    import app.auth.rbac as rbac_module

    orig = rbac_module.service_client
    rbac_module.service_client = fake_service_client_ctx
    try:
        client = TestClient(app)
        response = client.post(
            "/products",
            json={"name": "x", "slug": "x", "price_cents": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        rbac_module.service_client = orig
        fake_service_client.close()


def test_create_product_succeeds_for_admin(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "44444444-4444-4444-4444-444444444444")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "admin"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def create_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/products"
        return httpx.Response(
            201,
            json=[
                {
                    "id": "p2",
                    "name": "New Widget",
                    "slug": "new-widget",
                    "description": None,
                    "price_cents": 500,
                    "is_active": True,
                    "category_id": None,
                }
            ],
        )

    fake_write_client = httpx.Client(base_url="https://test-project.supabase.co/rest/v1", transport=httpx.MockTransport(create_handler))

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    from app.core.config import settings as settings_module

    settings_module.supabase_service_role_key = "test-service-role-key"

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[products_router.get_service_client] = _fake_service_client
    try:
        client = TestClient(app)
        response = client.post(
            "/products",
            json={"name": "New Widget", "slug": "new-widget", "price_cents": 500},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "new-widget"
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()


def test_get_product_by_slug_found():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/products"
        assert request.url.params["slug"] == "eq.test-widget"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "p3",
                    "name": "Test Widget",
                    "slug": "test-widget",
                    "description": "desc",
                    "price_cents": 1000,
                    "is_active": True,
                    "category_id": None,
                }
            ],
        )

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_anon_client():
        yield fake_client

    app.dependency_overrides[products_router.get_anon_client] = _fake_anon_client
    try:
        response = TestClient(app).get("/products/test-widget")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Widget"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_get_product_by_slug_not_found_returns_404():
    # Same response PostgREST gives whether the slug truly doesn't exist or
    # exists but is inactive and RLS already filtered it out — see the
    # comment in app/products/router.py for why that's intentional.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_anon_client():
        yield fake_client

    app.dependency_overrides[products_router.get_anon_client] = _fake_anon_client
    try:
        response = TestClient(app).get("/products/does-not-exist")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_update_product_requires_admin_role(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "77777777-7777-7777-7777-777777777777")

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
            "/products/p1",
            json={"price_cents": 500},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        rbac_module.service_client = orig
        fake_role_lookup_client.close()


def test_update_product_succeeds_for_admin(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "88888888-8888-8888-8888-888888888888")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "admin"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def patch_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.params["id"] == "eq.p1"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "p1",
                    "name": "Updated Widget",
                    "slug": "updated-widget",
                    "description": None,
                    "price_cents": 750,
                    "is_active": True,
                    "category_id": None,
                }
            ],
        )

    fake_write_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(patch_handler),
    )

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[products_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).patch(
            "/products/p1",
            json={"price_cents": 750},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["price_cents"] == 750
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()


def test_update_product_with_no_fields_is_400(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "99999999-9999-9999-9999-999999999999")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "admin"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    import app.auth.rbac as rbac_module

    orig = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client
    try:
        response = TestClient(app).patch(
            "/products/p1",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
    finally:
        rbac_module.service_client = orig
        fake_role_lookup_client.close()


def test_delete_product_not_found_returns_404(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "owner"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def delete_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    fake_write_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(delete_handler),
    )

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[products_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).delete(
            "/products/does-not-exist",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()


def test_delete_product_succeeds_for_admin(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "admin"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def delete_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.params["id"] == "eq.p1"
        return httpx.Response(200, json=[{"id": "p1"}])

    fake_write_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(delete_handler),
    )

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[products_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).delete(
            "/products/p1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()
