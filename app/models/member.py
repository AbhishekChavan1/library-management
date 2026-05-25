"""Member ORM model — library patrons who borrow books."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _generate_membership_id() -> str:
    """Generate a short membership ID like 'LIB-A1B2C3'."""
    return f"LIB-{uuid.uuid4().hex[:6].upper()}"


class Member(Base):
    """Library member / patron."""

    __tablename__ = "members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    membership_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, default=_generate_membership_id
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    membership_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="standard"
    )  # standard | premium
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    borrow_records = relationship("BorrowRecord", back_populates="member", lazy="selectin")
