"""Borrowing service — issue books, process returns, track overdue."""

import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import Book
from app.models.borrow_record import BorrowRecord
from app.models.member import Member
from app.schemas.borrowing import BorrowResponse
from app.schemas.common import PaginatedResponse


async def issue_book(
    db: AsyncSession,
    book_id: uuid.UUID,
    member_id: uuid.UUID,
    issued_by: uuid.UUID,
) -> BorrowResponse:
    """Issue a book to a member.

    Checks:
    - Book exists and has available copies
    - Member exists and is active
    - Member hasn't exceeded max borrow limit
    - Member doesn't already have this book checked out
    """
    # Check book
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    book = book_result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.available_copies <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No available copies of '{book.title}'",
        )

    # Check member
    member_result = await db.execute(select(Member).where(Member.id == member_id))
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if not member.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Member account is inactive"
        )

    # Check borrow limit
    active_count_result = await db.execute(
        select(func.count(BorrowRecord.id)).where(
            BorrowRecord.member_id == member_id,
            BorrowRecord.status == "borrowed",
        )
    )
    active_count = active_count_result.scalar() or 0
    if active_count >= settings.MAX_BOOKS_PER_MEMBER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Member has reached the limit of {settings.MAX_BOOKS_PER_MEMBER} "
            "borrowed books",
        )

    # Check if member already has this book
    duplicate_result = await db.execute(
        select(BorrowRecord).where(
            BorrowRecord.book_id == book_id,
            BorrowRecord.member_id == member_id,
            BorrowRecord.status == "borrowed",
        )
    )
    if duplicate_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member already has this book checked out",
        )

    # Create borrow record
    now = datetime.now(UTC)
    record = BorrowRecord(
        book_id=book_id,
        member_id=member_id,
        issued_by=issued_by,
        borrow_date=now,
        due_date=now + timedelta(days=settings.BORROW_PERIOD_DAYS),
        status="borrowed",
    )
    db.add(record)

    # Decrement available copies
    book.available_copies -= 1

    await db.flush()
    await db.refresh(record)
    return _to_response(record)


async def return_book(db: AsyncSession, record_id: uuid.UUID) -> BorrowResponse:
    """Process a book return.

    Sets return_date, increments available_copies, updates status.
    """
    result = await db.execute(select(BorrowRecord).where(BorrowRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow record not found")
    if record.status == "returned":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book already returned")

    # Update record
    record.return_date = datetime.now(UTC)
    record.status = "returned"

    # Increment available copies
    book_result = await db.execute(select(Book).where(Book.id == record.book_id))
    book = book_result.scalar_one_or_none()
    if book:
        book.available_copies = min(book.available_copies + 1, book.total_copies)

    await db.flush()
    await db.refresh(record)
    return _to_response(record)


async def get_overdue_records(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse[BorrowResponse]:
    """List all currently overdue borrow records."""
    now = datetime.now(UTC)

    base_filter = (
        BorrowRecord.due_date < now,
        BorrowRecord.return_date.is_(None),
        BorrowRecord.status != "returned",
    )

    count_query = select(func.count(BorrowRecord.id)).where(*base_filter)
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        select(BorrowRecord)
        .where(*base_filter)
        .offset((page - 1) * size)
        .limit(size)
        .order_by(BorrowRecord.due_date)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    # Also update their status to 'overdue'
    for record in records:
        if record.status != "overdue":
            record.status = "overdue"

    return PaginatedResponse(
        items=[_to_response(r) for r in records],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def get_borrow_history(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    member_id: uuid.UUID | None = None,
    book_id: uuid.UUID | None = None,
    status_filter: str | None = None,
) -> PaginatedResponse[BorrowResponse]:
    """Get borrow history with optional filters."""
    query = select(BorrowRecord)
    count_query = select(func.count(BorrowRecord.id))

    if member_id:
        query = query.where(BorrowRecord.member_id == member_id)
        count_query = count_query.where(BorrowRecord.member_id == member_id)
    if book_id:
        query = query.where(BorrowRecord.book_id == book_id)
        count_query = count_query.where(BorrowRecord.book_id == book_id)
    if status_filter:
        query = query.where(BorrowRecord.status == status_filter)
        count_query = count_query.where(BorrowRecord.status == status_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(BorrowRecord.borrow_date.desc())
    result = await db.execute(query)
    records = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(r) for r in records],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


def _to_response(record: BorrowRecord) -> BorrowResponse:
    return BorrowResponse(
        id=record.id,
        book_id=record.book_id,
        book_title=record.book.title if record.book else None,
        book_isbn=record.book.isbn if record.book else None,
        member_id=record.member_id,
        member_name=record.member.name if record.member else None,
        membership_id=record.member.membership_id if record.member else None,
        issued_by=record.issued_by,
        borrow_date=record.borrow_date,
        due_date=record.due_date,
        return_date=record.return_date,
        status=record.status,
    )
