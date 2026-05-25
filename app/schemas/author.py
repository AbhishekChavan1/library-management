"""Author schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuthorCreate(BaseModel):
    """Create a new author."""

    name: str
    bio: str | None = None


class AuthorUpdate(BaseModel):
    """Update an author."""

    name: str | None = None
    bio: str | None = None


class AuthorResponse(BaseModel):
    """Author detail response."""

    id: uuid.UUID
    name: str
    bio: str | None
    created_at: datetime
    book_count: int = 0

    model_config = {"from_attributes": True}
