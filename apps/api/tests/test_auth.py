"""
Tests for app.auth.security. The valid-token case signs its own JWT with a
locally generated RSA keypair and monkeypatches get_jwks_client() to return
a fake JWKS client that hands back that keypair's public key — this avoids
any real network call to Supabase's JWKS endpoint, which this sandbox's
network egress can't reach anyway (see docs/DEVELOPMENT_LOG.md, Stage 3
session notes).
"""
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import security
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_me_without_token_is_401():
    response = client.get("/me")
    assert response.status_code == 401


def test_me_with_garbage_token_is_401():
    response = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_me_with_valid_token_returns_identity(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://test-project.supabase.co")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str):
            return FakeSigningKey(public_key)

    monkeypatch.setattr(security, "get_jwks_client", lambda: FakeJWKSClient())

    now = datetime.now(timezone.utc)
    token = pyjwt.encode(
        {
            "sub": "11111111-1111-1111-1111-111111111111",
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

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "11111111-1111-1111-1111-111111111111"
    assert body["postgres_role"] == "authenticated"


def test_me_with_expired_token_is_401(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://test-project.supabase.co")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str):
            return FakeSigningKey(public_key)

    monkeypatch.setattr(security, "get_jwks_client", lambda: FakeJWKSClient())

    now = datetime.now(timezone.utc)
    expired_token = pyjwt.encode(
        {
            "sub": "22222222-2222-2222-2222-222222222222",
            "role": "authenticated",
            "aud": "authenticated",
            "iss": f"{settings.supabase_url}/auth/v1",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    response = client.get(
        "/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
