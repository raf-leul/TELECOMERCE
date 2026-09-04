from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    parent_category_id: str | None = None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    parent_category_id: str | None = None
