"""
Shared plumbing for endpoints that talk to Supabase's PostgREST API.
Factored out of app/products/router.py so app/categories/router.py (and
future catalog-adjacent modules) don't duplicate it — see docs/DECISIONS.md
for why this was pulled out after the products module was first built.
"""
from __future__ import annotations

from typing import Iterator

import httpx
from fastapi import HTTPException, status

from app.core.supabase_client import anon_client, service_client


def get_anon_client() -> Iterator[httpx.Client]:
    with anon_client() as client:
        yield client


def get_service_client() -> Iterator[httpx.Client]:
    try:
        with service_client() as client:
            yield client
    except RuntimeError as exc:
        # service_client() raises RuntimeError if SUPABASE_SERVICE_ROLE_KEY
        # isn't configured — a real bug found by booting the real server
        # without that env var set (see docs/DECISIONS.md): this wasn't
        # caught anywhere and leaked as an unhandled 500. Every endpoint
        # using get_service_client (products/categories writes, all of
        # cart) goes through this one place, so fixing it here covers all
        # of them at once rather than wrapping each route individually.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "SERVICE_MISCONFIGURED",
                    "message": "This operation is temporarily unavailable.",
                }
            },
        ) from exc


def translate_postgrest_error(exc: Exception) -> HTTPException:
    # Never pass raw PostgREST/Postgres error bodies straight to the client
    # (master instructions section 26 — don't leak internals). Catches both
    # httpx.HTTPStatusError (PostgREST returned an error response) and
    # httpx.RequestError (couldn't reach Supabase at all) — both should
    # look the same to the API's caller, not leak as an unhandled 500 (see
    # docs/DECISIONS.md, "Bug found via real server testing").
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "CATALOG_BACKEND_ERROR",
                "message": "The catalog service is temporarily unavailable.",
            }
        },
    )
