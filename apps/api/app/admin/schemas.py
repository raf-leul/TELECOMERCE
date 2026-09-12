from __future__ import annotations

from pydantic import BaseModel


class AdminProductOut(BaseModel):
    """
    Same shape as ProductOut but reachable regardless of is_active — the
    public /products list is RLS-filtered to active only (Stage 4); this
    admin view uses the service-role client so drafts/inactive products
    are visible too, which is the whole point of an admin product list.
    """

    id: str
    name: str
    slug: str
    description: str | None
    price_cents: int
    is_active: bool
    category_id: str | None


class AdminOrderOut(BaseModel):
    id: str
    user_id: str | None
    status: str
    subtotal_cents: int
    created_at: str


class OrderStatusCount(BaseModel):
    status: str
    count: int


class LowStockProduct(BaseModel):
    product_id: str
    product_name: str
    quantity_available: int


class AdminOverviewOut(BaseModel):
    total_orders: int
    orders_by_status: list[OrderStatusCount]
    revenue_cents: int
    low_stock_products: list[LowStockProduct]
