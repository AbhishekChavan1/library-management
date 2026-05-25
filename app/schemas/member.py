"""Member schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class MemberCreate(BaseModel):
    """Register a new library member."""

    name: str
    email: EmailStr
    phone: str | None = None
    membership_type: str = "standard"  # standard | premium


class MemberUpdate(BaseModel):
    """Update member details."""

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    membership_type: str | None = None
    is_active: bool | None = None


class MemberResponse(BaseModel):
    """Member detail response."""

    id: uuid.UUID
    membership_id: str
    name: str
    email: str
    phone: str | None
    membership_type: str
    is_active: bool
    joined_at: datetime
    active_borrows: int = 0

    model_config = {"from_attributes": True}
