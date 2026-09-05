"""
Verifies Supabase-issued access tokens (JWTs) locally against the project's
published JWKS, so every protected request doesn't need a network round
trip to Supabase's /auth/v1/user endpoint.

Endpoint and caching approach follow current Supabase guidance (checked
2026-09-02, see docs/DECISIONS.md): fetch
`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, cache the key set, verify
signature + `iss` + `aud` ("authenticated") + `exp` locally.

The JWKS client is created lazily and cached at module level so it can be
swapped out in tests (see apps/api/tests/test_auth.py) without any network
access.
"""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)

_jwks_client: PyJWKClient | None = None


def _jwks_url() -> str:
    return f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"


def get_jwks_client() -> PyJWKClient:
    """
    Returns a cached PyJWKClient. Tests override this via FastAPI's
    dependency_overrides (or by monkeypatching this function directly) so
    no real network call happens during unit tests.
    """
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(_jwks_url(), cache_keys=True)
    return _jwks_client


class VerifiedUser:
    """Minimal identity extracted from a verified Supabase access token."""

    def __init__(self, claims: dict):
        self.claims = claims
        self.id: str = claims["sub"]
        # This is the Postgres role Supabase puts in the JWT (typically
        # "authenticated"), NOT the app-level profiles.role enum from
        # Stage 2. Looking up profiles.role for authorization decisions is
        # left to whichever endpoint needs it (not built yet in this
        # stage) rather than done here, to keep this dependency's job
        # limited to "is this token valid, and whose is it".
        self.postgres_role: str | None = claims.get("role")


def verify_token(token: str, jwks_client: PyJWKClient | None = None) -> dict:
    """
    Verifies a Supabase access token's signature and standard claims.
    Raises jwt exceptions on failure — callers translate those to HTTP 401.
    """
    client = jwks_client if jwks_client is not None else get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=f"{settings.supabase_url}/auth/v1",
    )
    return claims


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> VerifiedUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001 - any verification failure -> 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return VerifiedUser(claims)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> VerifiedUser | None:
    """
    Like get_current_user, but returns None instead of raising 401 when no
    token is present — for endpoints (like cart) that support both guest
    and authenticated access. A present-but-invalid token still raises 401
    rather than silently falling back to guest, so a typo'd/expired token
    doesn't quietly downgrade someone to an empty guest cart.
    """
    if credentials is None or not credentials.credentials:
        return None
    return get_current_user(credentials)
