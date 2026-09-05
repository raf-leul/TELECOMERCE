"""
Product catalog endpoints.

Reads use the anon client and rely entirely on the RLS policies from Stage 2
(supabase/migrations/0002_catalog.sql) — anon/authenticated can only ever
see is_active=true products, enforced by Postgres, not by this code. Writes
use the service-role client (bypassing RLS, since no client-writable policy
exists on products by design) and are gated by require_role("admin",
"owner") from app.auth.rbac.

get_anon_client/get_service_client/translate_postgrest_error are shared
with app.categories.router — see app.core.postgrest_deps. Re-imported here
under their original names so existing test overrides
(app.dependency_overrides[products_router.get_anon_client] = ...) keep
working unchanged.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.rbac import require_role
from app.core.postgrest_deps import get_anon_client, get_service_client
from app.core.postgrest_deps import translate_postgrest_error as _translate_postgrest_error
from app.products.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


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


@router.get("/{slug}", response_model=ProductOut)
def get_product(
    slug: str, client: httpx.Client = Depends(get_anon_client)
) -> dict:
    try:
        response = client.get(
            "/products",
            params={
                "select": "id,name,slug,description,price_cents,is_active,category_id",
                "slug": f"eq.{slug}",
                "limit": "1",
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    rows = response.json()
    if not rows:
        # Deliberately the same 404 whether the product doesn't exist at
        # all or exists but is inactive (RLS already filtered it out
        # before this code ever saw it) — not distinguishing the two
        # avoids leaking which slugs exist as drafts.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return rows[0]


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


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_role("admin", "owner"))],
)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    client: httpx.Client = Depends(get_service_client),
) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NO_FIELDS_TO_UPDATE",
                    "message": "Provide at least one field to update.",
                }
            },
        )

    try:
        response = client.patch(
            "/products",
            params={"id": f"eq.{product_id}"},
            json=changes,
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    rows = response.json()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return rows[0]


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_role("admin", "owner"))],
)
def delete_product(
    product_id: str,
    client: httpx.Client = Depends(get_service_client),
) -> None:
    try:
        response = client.delete(
            "/products",
            params={"id": f"eq.{product_id}"},
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    rows = response.json()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
