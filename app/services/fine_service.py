"""Fine/Penalty service — manage fines and overdue penalties."""

import math
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.borrow_record import BorrowRecord
from app.models.fine import Fine
from app.models.member import Member
from app.schemas.common import PaginatedResponse
from app.schemas.fine import FineCreate, FinePayment, FineResponse


async def create_fine(db: AsyncSession, fine_data: FineCreate) -> FineResponse:
    """Create a fine for a member.

    Checks:
    - Borrow record exists
    - Member exists
    - Fine doesn't already exist for this borrow record
    """
    # Check borrow record
    record_result = await db.execute(
        select(BorrowRecord).where(BorrowRecord.id == fine_data.borrow_record_id)
    )
    record = record_result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow record not found")

    # Check member
    member_result = await db.execute(select(Member).where(Member.id == fine_data.member_id))
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Check for duplicate fine
    duplicate_result = await db.execute(
        select(Fine).where(
            Fine.borrow_record_id == fine_data.borrow_record_id,
            Fine.status != "paid",
        )
    )
    if duplicate_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An unpaid fine already exists for this borrow record",
        )

    # Cap the fine at maximum allowed
    amount = fine_data.amount
    max_fine = Decimal(str(settings.MAX_FINE_PER_BOOK))
    if amount > max_fine:
        amount = max_fine

    # Create fine
    fine = Fine(
        borrow_record_id=fine_data.borrow_record_id,
        member_id=fine_data.member_id,
        amount=amount,
        reason=fine_data.reason,
        status="unpaid",
    )
    db.add(fine)
    await db.flush()
    await db.refresh(fine)
    return _to_response(fine)


async def calculate_overdue_fine(db: AsyncSession, borrow_record_id: uuid.UUID) -> Decimal:
    """Calculate the fine amount for an overdue book."""
    result = await db.execute(select(BorrowRecord).where(BorrowRecord.id == borrow_record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow record not found")

    # Calculate days overdue
    now = datetime.now(UTC)
    if now <= record.due_date:
        return Decimal("0.00")

    days_overdue = (now - record.due_date).days
    fine_amount = Decimal(days_overdue) * Decimal(settings.FINE_PER_DAY)

    # Cap the fine
    max_fine = Decimal(settings.MAX_FINE_PER_BOOK)
    if fine_amount > max_fine:
        fine_amount = max_fine

    return fine_amount


async def get_fine(db: AsyncSession, fine_id: uuid.UUID) -> FineResponse:
    """Get a specific fine."""
    result = await db.execute(select(Fine).where(Fine.id == fine_id))
    fine = result.scalar_one_or_none()
    if not fine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found")
    return _to_response(fine)


async def list_fines(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    member_id: uuid.UUID | None = None,
    status_filter: str | None = None,
) -> PaginatedResponse[FineResponse]:
    """List fines with optional filters."""
    query = select(Fine)
    count_query = select(func.count(Fine.id))

    if member_id:
        query = query.where(Fine.member_id == member_id)
        count_query = count_query.where(Fine.member_id == member_id)
    if status_filter:
        query = query.where(Fine.status == status_filter)
        count_query = count_query.where(Fine.status == status_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Fine.created_at.desc())
    result = await db.execute(query)
    fines = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(f) for f in fines],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def pay_fine(db: AsyncSession, fine_id: uuid.UUID, payment: FinePayment) -> FineResponse:
    """Pay a fine or partial payment.

    For MVP, we require full payment. Partial payments can be added in future.
    """
    result = await db.execute(select(Fine).where(Fine.id == fine_id))
    fine = result.scalar_one_or_none()
    if not fine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found")

    if fine.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fine already paid")

    if payment.amount != fine.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount must be {fine.amount} (partial payments not supported)",
        )

    fine.status = "paid"
    fine.paid_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(fine)
    return _to_response(fine)


async def waive_fine(db: AsyncSession, fine_id: uuid.UUID) -> FineResponse:
    """Waive a fine (admin only)."""
    result = await db.execute(select(Fine).where(Fine.id == fine_id))
    fine = result.scalar_one_or_none()
    if not fine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found")

    if fine.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot waive paid fine"
        )

    fine.status = "waived"
    fine.paid_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(fine)
    return _to_response(fine)


async def get_member_total_fines(db: AsyncSession, member_id: uuid.UUID) -> Decimal:
    """Get total unpaid fines for a member."""
    result = await db.execute(
        select(func.sum(Fine.amount)).where(
            Fine.member_id == member_id,
            Fine.status == "unpaid",
        )
    )
    total = result.scalar() or Decimal("0.00")
    return Decimal(total) if total else Decimal("0.00")


def _to_response(fine: Fine) -> FineResponse:
    return FineResponse(
        id=fine.id,
        borrow_record_id=fine.borrow_record_id,
        member_id=fine.member_id,
        member_name=fine.member.name if fine.member else None,
        membership_id=fine.member.membership_id if fine.member else None,
        amount=fine.amount,
        reason=fine.reason,
        created_at=fine.created_at,
        paid_at=fine.paid_at,
        status=fine.status,
    )
