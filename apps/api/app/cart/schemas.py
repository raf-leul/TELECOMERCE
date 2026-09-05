from __future__ import annotations

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemOut(BaseModel):
    product_id: str
    name: str
    slug: str
    quantity: int
    # Server-computed, never trust a client-supplied price/total anywhere
    # in this response (master instructions section 27).
    unit_price_cents: int
    line_total_cents: int


class CartOut(BaseModel):
    cart_id: str
    items: list[CartItemOut]
    subtotal_cents: int
