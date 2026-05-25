"""Borrowing schemas — issue, return, history."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BorrowRequest(BaseModel):
    """Issue a book to a member."""

    book_id: uuid.UUID
    member_id: uuid.UUID


class BorrowResponse(BaseModel):
    """Borrow record response."""

    id: uuid.UUID
    book_id: uuid.UUID
    book_title: str | None = None
    book_isbn: str | None = None
    member_id: uuid.UUID
    member_name: str | None = None
    membership_id: str | None = None
    issued_by: uuid.UUID
    borrow_date: datetime
    due_date: datetime
    return_date: datetime | None
    status: str

    model_config = {"from_attributes": True}
