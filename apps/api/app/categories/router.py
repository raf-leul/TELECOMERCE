"""
Category endpoints. Same pattern as app.products.router: anon reads rely
entirely on Stage 2's RLS policies (categories are not sensitive, so
everyone can read them — see supabase/migrations/0002_catalog.sql), and
writes go through the service-role client, gated by
require_role("admin", "owner").
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.rbac import require_role
from app.categories.schemas import CategoryCreate, CategoryOut
from app.core.postgrest_deps import get_anon_client, get_service_client
from app.core.postgrest_deps import translate_postgrest_error as _translate_postgrest_error

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(client: httpx.Client = Depends(get_anon_client)) -> list[dict]:
    try:
        response = client.get(
            "/categories",
            params={
                "select": "id,name,slug,parent_category_id",
                "order": "name.asc",
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc
    return response.json()


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "owner"))],
)
def create_category(
    payload: CategoryCreate,
    client: httpx.Client = Depends(get_service_client),
) -> dict:
    try:
        response = client.post(
            "/categories",
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
                    "message": "Category was not returned after creation.",
                }
            },
        )
    return rows[0]
