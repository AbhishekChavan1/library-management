"""BorrowRecord ORM model — tracks book checkouts and returns."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BorrowRecord(Base):
    """Tracks a single book borrow/return transaction."""

    __tablename__ = "borrow_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=False
    )
    issued_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    borrow_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    return_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="borrowed"
    )  # borrowed | returned | overdue

    # Relationships
    book = relationship("Book", back_populates="borrow_records", lazy="selectin")
    member = relationship("Member", back_populates="borrow_records", lazy="selectin")
    issuer = relationship("User", lazy="selectin")
