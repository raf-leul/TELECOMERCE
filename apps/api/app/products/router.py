"""
Product catalog endpoints.

Reads use the anon client and rely entirely on the RLS policies from Stage 2
(supabase/migrations/0002_catalog.sql) — anon/authenticated can only ever
see is_active=true products, enforced by Postgres, not by this code. Writes
use the service-role client (bypassing RLS, since no client-writable policy
exists on products by design) and are gated by require_role("admin",
"owner") from app.auth.rbac.
"""
from __future__ import annotations

from typing import Iterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.rbac import require_role
from app.core.supabase_client import anon_client, service_client
from app.products.schemas import ProductCreate, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


def get_anon_client() -> Iterator[httpx.Client]:
    with anon_client() as client:
        yield client


def get_service_client() -> Iterator[httpx.Client]:
    with service_client() as client:
        yield client


def _translate_postgrest_error(exc: Exception) -> HTTPException:
    # Never pass raw PostgREST/Postgres error bodies straight to the client
    # (master instructions section 26 — don't leak internals). Map to a
    # generic structured error and let server-side logs carry the detail.
    # Catches both httpx.HTTPStatusError (PostgREST returned an error
    # response) and httpx.RequestError (couldn't reach Supabase at all,
    # e.g. misconfigured URL/key or a network failure) — both should look
    # the same to the API's caller, not leak as an unhandled 500.
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "CATALOG_BACKEND_ERROR",
                "message": "The catalog service is temporarily unavailable.",
            }
        },
    )


@router.get("", response_model=list[ProductOut])
def list_products(client: httpx.Client = Depends(get_anon_client)) -> list[dict]:
    try:
        response = client.get(
            "/products",
            params={
                "select": "id,name,slug,description,price_cents,is_active,category_id",
                "order": "created_at.desc",
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc
    return response.json()


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "owner"))],
)
def create_product(
    payload: ProductCreate,
    client: httpx.Client = Depends(get_service_client),
) -> dict:
    try:
        response = client.post(
            "/products",
            json=payload.model_dump(),
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    rows = response.json()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "CATALOG_BACKEND_ERROR",
                    "message": "Product was not returned after creation.",
                }
            },
        )
    return rows[0]
