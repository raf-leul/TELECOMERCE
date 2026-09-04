"""
Tests for app.categories.router. Same approach as test_products.py:
httpx.MockTransport intercepts every PostgREST call, no real network.
"""
from datetime import datetime, timedelta, timezone

import httpx
import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import security
from app.categories import router as categories_router
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


def test_list_categories_public():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/categories"
        return httpx.Response(
            200,
            json=[{"id": "c1", "name": "Electronics", "slug": "electronics", "parent_category_id": None}],
        )

    fake_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(handler),
    )

    def _fake_anon_client():
        yield fake_client

    app.dependency_overrides[categories_router.get_anon_client] = _fake_anon_client
    try:
        response = TestClient(app).get("/categories")
        assert response.status_code == 200
        assert response.json()[0]["slug"] == "electronics"
    finally:
        app.dependency_overrides.clear()
        fake_client.close()


def test_create_category_requires_auth():
    response = TestClient(app).post("/categories", json={"name": "x", "slug": "x"})
    assert response.status_code == 401


def test_create_category_requires_admin_role(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "55555555-5555-5555-5555-555555555555")

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
        response = TestClient(app).post(
            "/categories",
            json={"name": "x", "slug": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        rbac_module.service_client = orig
        fake_role_lookup_client.close()


def test_create_category_succeeds_for_admin(_patch_jwks, rsa_keypair):
    private_key, _ = rsa_keypair
    token = _make_token(private_key, "66666666-6666-6666-6666-666666666666")

    def profile_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"role": "owner"}])

    fake_role_lookup_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(profile_handler),
    )

    def create_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/categories"
        return httpx.Response(
            201,
            json=[{"id": "c2", "name": "Books", "slug": "books", "parent_category_id": None}],
        )

    fake_write_client = httpx.Client(
        base_url="https://test-project.supabase.co/rest/v1",
        transport=httpx.MockTransport(create_handler),
    )

    import app.auth.rbac as rbac_module

    orig_rbac_service_client = rbac_module.service_client
    rbac_module.service_client = lambda: fake_role_lookup_client

    def _fake_service_client():
        yield fake_write_client

    app.dependency_overrides[categories_router.get_service_client] = _fake_service_client
    try:
        response = TestClient(app).post(
            "/categories",
            json={"name": "Books", "slug": "books"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "books"
    finally:
        rbac_module.service_client = orig_rbac_service_client
        app.dependency_overrides.clear()
        fake_role_lookup_client.close()
        fake_write_client.close()
