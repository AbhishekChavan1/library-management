"""Hold/Reservation schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class HoldCreate(BaseModel):
    """Create a hold on a book."""

    book_id: uuid.UUID
    member_id: uuid.UUID


class HoldUpdate(BaseModel):
    """Update a hold."""

    status: str | None = None


class HoldResponse(BaseModel):
    """Hold response."""

    id: uuid.UUID
    book_id: uuid.UUID
    book_title: str | None = None
    member_id: uuid.UUID
    member_name: str | None = None
    membership_id: str | None = None
    hold_date: datetime
    expires_at: datetime
    fulfilled_date: datetime | None = None
    status: str

    model_config = {"from_attributes": True}
