"""Fine/Penalty schemas."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class FineCreate(BaseModel):
    """Create a fine."""

    borrow_record_id: uuid.UUID
    member_id: uuid.UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    reason: str  # overdue | damage | lost


class FinePayment(BaseModel):
    """Pay a fine."""

    amount: Decimal = Field(..., gt=0, decimal_places=2)


class FineResponse(BaseModel):
    """Fine response."""

    id: uuid.UUID
    borrow_record_id: uuid.UUID
    member_id: uuid.UUID
    member_name: str | None = None
    membership_id: str | None = None
    amount: Decimal
    reason: str
    created_at: datetime
    paid_at: datetime | None = None
    status: str

    model_config = {"from_attributes": True}
