"""
Thin wrapper around Supabase's auto-generated PostgREST API. Deliberately
not using the full supabase-py SDK — for the handful of operations this
backend needs (a few reads, a few admin writes, one profile-role lookup),
raw httpx calls against PostgREST are simpler to reason about and to test
via a mocked transport (see apps/api/tests), with no hidden SDK behavior.

Two client builders:
- `anon_client()`: uses the anon/publishable key. Subject to RLS exactly
  like a browser client would be — safe for public reads.
- `service_client()`: uses the service-role key. Bypasses RLS entirely.
  Only used for operations that are intentionally not exposed to
  anon/authenticated roles at the database level (see docs/DATABASE.md) —
  admin catalog writes, and reading another user's profiles.role for
  authorization checks.
"""
from __future__ import annotations

import httpx

from app.core.config import settings


def _rest_url() -> str:
    return f"{settings.supabase_url}/rest/v1"


def anon_client() -> httpx.Client:
    return httpx.Client(
        base_url=_rest_url(),
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {settings.supabase_anon_key}",
        },
        timeout=10.0,
    )


def service_client() -> httpx.Client:
    if not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured. Admin operations "
            "cannot run without it. Set it in apps/api/.env (never commit it)."
        )
    return httpx.Client(
        base_url=_rest_url(),
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        },
        timeout=10.0,
    )
