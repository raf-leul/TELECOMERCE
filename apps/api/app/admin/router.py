"""
Admin-only endpoints. Everything here uses the service-role client and is
gated by require_role("admin", "owner", "staff") — the ownership
restrictions that apply to the regular /orders and /products endpoints
(a user only sees their own orders; only active products are public) are
intentionally bypassed here, because that's the entire point of an admin
view. Nothing new is exposed to non-admins: the gate is checked before any
query runs.

Aggregation for the overview endpoint (order counts by status, revenue)
is done in Python after fetching rows, not via a database view or RPC —
deliberately simple for the current data volume (master instructions
section 64, don't over-engineer). Revisit with a proper SQL aggregation
or materialized view if/when order volume makes fetching all rows
impractical.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query

from app.admin.schemas import (
    AdminOrderOut,
    AdminOverviewOut,
    AdminProductOut,
    LowStockProduct,
    OrderStatusCount,
)
from app.auth.rbac import require_role
from app.core.postgrest_deps import get_service_client
from app.core.postgrest_deps import translate_postgrest_error as _translate_postgrest_error

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin", "owner", "staff"))],
)

# Orders in these statuses represent money actually received. Excludes
# pending_payment (not yet paid), cancelled, and refunded (paid but given
# back) from the revenue figure.
REVENUE_STATUSES = {"paid", "processing", "packed", "shipped", "delivered"}


@router.get("/products", response_model=list[AdminProductOut])
def list_all_products(client: httpx.Client = Depends(get_service_client)) -> list[dict]:
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


@router.get("/orders", response_model=list[AdminOrderOut])
def list_all_orders(client: httpx.Client = Depends(get_service_client)) -> list[dict]:
    try:
        response = client.get(
            "/orders",
            params={
                "select": "id,user_id,status,subtotal_cents,created_at",
                "order": "created_at.desc",
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc
    return response.json()


@router.get("/overview", response_model=AdminOverviewOut)
def get_overview(
    low_stock_threshold: int = Query(default=5, ge=0),
    client: httpx.Client = Depends(get_service_client),
) -> AdminOverviewOut:
    try:
        orders_response = client.get("/orders", params={"select": "status,subtotal_cents"})
        orders_response.raise_for_status()
        orders = orders_response.json()

        inventory_response = client.get(
            "/inventory",
            params={
                "select": "product_id,quantity_available,products(name)",
                "quantity_available": f"lte.{low_stock_threshold}",
            },
        )
        inventory_response.raise_for_status()
        low_stock_rows = inventory_response.json()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    status_counts: dict[str, int] = {}
    revenue_cents = 0
    for order in orders:
        status_counts[order["status"]] = status_counts.get(order["status"], 0) + 1
        if order["status"] in REVENUE_STATUSES:
            revenue_cents += order["subtotal_cents"]

    return AdminOverviewOut(
        total_orders=len(orders),
        orders_by_status=[
            OrderStatusCount(status=status, count=count)
            for status, count in sorted(status_counts.items())
        ],
        revenue_cents=revenue_cents,
        low_stock_products=[
            LowStockProduct(
                product_id=row["product_id"],
                product_name=(row.get("products") or {}).get("name", "Unknown"),
                quantity_available=row["quantity_available"],
            )
            for row in low_stock_rows
        ],
    )
