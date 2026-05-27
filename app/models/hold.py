"""Hold/Reservation ORM model — tracks book holds by members."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Hold(Base):
    """Tracks a book hold/reservation by a member."""

    __tablename__ = "holds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id"), nullable=False
    )
    hold_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC) + timedelta(days=7),
    )
    fulfilled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active | fulfilled | expired | cancelled

    # Relationships
    book = relationship("Book", lazy="selectin")
    member = relationship("Member", lazy="selectin")
