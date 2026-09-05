from __future__ import annotations

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    price_cents: int
    is_active: bool
    category_id: str | None = None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    description: str | None = None
    price_cents: int = Field(ge=0)
    category_id: str | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    """All fields optional — PATCH applies only what's provided."""

    name: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    category_id: str | None = None
    is_active: bool | None = None
