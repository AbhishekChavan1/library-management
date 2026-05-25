"""Category schemas."""

import uuid

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    """Create a new category."""

    name: str
    description: str | None = None


class CategoryUpdate(BaseModel):
    """Update a category."""

    name: str | None = None
    description: str | None = None


class CategoryResponse(BaseModel):
    """Category detail response."""

    id: uuid.UUID
    name: str
    description: str | None
    book_count: int = 0

    model_config = {"from_attributes": True}
