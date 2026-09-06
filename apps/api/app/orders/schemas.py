from __future__ import annotations

from pydantic import BaseModel, Field

from app.orders.state_machine import ALL_STATUSES


class OrderItemOut(BaseModel):
    product_id: str | None
    product_name: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int


class OrderOut(BaseModel):
    id: str
    status: str
    subtotal_cents: int
    items: list[OrderItemOut]
    created_at: str


class OrderStatusUpdate(BaseModel):
    status: str = Field(description=f"One of: {', '.join(sorted(ALL_STATUSES))}")
