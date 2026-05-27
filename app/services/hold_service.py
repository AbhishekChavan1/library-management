"""Hold/Reservation service — manage book holds and reservations."""

import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.hold import Hold
from app.models.member import Member
from app.schemas.common import PaginatedResponse
from app.schemas.hold import HoldCreate, HoldResponse


async def create_hold(db: AsyncSession, hold_data: HoldCreate) -> HoldResponse:
    """Create a hold on a book for a member.

    Checks:
    - Book exists
    - Member exists and is active
    - Member doesn't already have an active hold on this book
    """
    # Check book
    book_result = await db.execute(select(Book).where(Book.id == hold_data.book_id))
    book = book_result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    # Check member
    member_result = await db.execute(select(Member).where(Member.id == hold_data.member_id))
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if not member.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Member account is inactive"
        )

    # Check for duplicate active hold
    duplicate_result = await db.execute(
        select(Hold).where(
            Hold.book_id == hold_data.book_id,
            Hold.member_id == hold_data.member_id,
            Hold.status == "active",
        )
    )
    if duplicate_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member already has an active hold on this book",
        )

    # Create hold
    now = datetime.now(UTC)
    hold = Hold(
        book_id=hold_data.book_id,
        member_id=hold_data.member_id,
        hold_date=now,
        expires_at=now + timedelta(days=7),
        status="active",
    )
    db.add(hold)
    await db.flush()
    await db.refresh(hold)
    return _to_response(hold)


async def get_hold(db: AsyncSession, hold_id: uuid.UUID) -> HoldResponse:
    """Get a specific hold."""
    result = await db.execute(select(Hold).where(Hold.id == hold_id))
    hold = result.scalar_one_or_none()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    return _to_response(hold)


async def list_holds(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    member_id: uuid.UUID | None = None,
    book_id: uuid.UUID | None = None,
    status_filter: str | None = None,
) -> PaginatedResponse[HoldResponse]:
    """List holds with optional filters."""
    query = select(Hold)
    count_query = select(func.count(Hold.id))

    if member_id:
        query = query.where(Hold.member_id == member_id)
        count_query = count_query.where(Hold.member_id == member_id)
    if book_id:
        query = query.where(Hold.book_id == book_id)
        count_query = count_query.where(Hold.book_id == book_id)
    if status_filter:
        query = query.where(Hold.status == status_filter)
        count_query = count_query.where(Hold.status == status_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Hold.hold_date)
    result = await db.execute(query)
    holds = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(h) for h in holds],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def cancel_hold(db: AsyncSession, hold_id: uuid.UUID) -> HoldResponse:
    """Cancel an active hold."""
    result = await db.execute(select(Hold).where(Hold.id == hold_id))
    hold = result.scalar_one_or_none()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    if hold.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel hold with status '{hold.status}'",
        )

    hold.status = "cancelled"
    await db.flush()
    await db.refresh(hold)
    return _to_response(hold)


async def fulfill_hold(db: AsyncSession, hold_id: uuid.UUID) -> HoldResponse:
    """Fulfill a hold (book becomes available for member to pick up)."""
    result = await db.execute(select(Hold).where(Hold.id == hold_id))
    hold = result.scalar_one_or_none()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    if hold.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fulfill hold with status '{hold.status}'",
        )

    hold.status = "fulfilled"
    hold.fulfilled_date = datetime.now(UTC)
    await db.flush()
    await db.refresh(hold)
    return _to_response(hold)


async def expire_holds(db: AsyncSession) -> int:
    """Expire all holds that have passed their expiration date."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(Hold).where(
            Hold.expires_at < now,
            Hold.status == "active",
        )
    )
    holds = result.scalars().all()

    for hold in holds:
        hold.status = "expired"

    await db.flush()
    return len(holds)


def _to_response(hold: Hold) -> HoldResponse:
    return HoldResponse(
        id=hold.id,
        book_id=hold.book_id,
        book_title=hold.book.title if hold.book else None,
        member_id=hold.member_id,
        member_name=hold.member.name if hold.member else None,
        membership_id=hold.member.membership_id if hold.member else None,
        hold_date=hold.hold_date,
        expires_at=hold.expires_at,
        fulfilled_date=hold.fulfilled_date,
        status=hold.status,
    )
