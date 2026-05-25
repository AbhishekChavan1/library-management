"""Book schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BookCreate(BaseModel):
    """Create a new book."""

    isbn: str
    title: str
    author_id: uuid.UUID
    category_id: uuid.UUID | None = None
    total_copies: int = 1
    year_published: int | None = None
    description: str | None = None


class BookUpdate(BaseModel):
    """Update an existing book (all fields optional)."""

    title: str | None = None
    author_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    total_copies: int | None = None
    year_published: int | None = None
    description: str | None = None


class BookResponse(BaseModel):
    """Book detail response."""

    id: uuid.UUID
    isbn: str
    title: str
    author_id: uuid.UUID
    author_name: str | None = None
    category_id: uuid.UUID | None
    category_name: str | None = None
    total_copies: int
    available_copies: int
    year_published: int | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
