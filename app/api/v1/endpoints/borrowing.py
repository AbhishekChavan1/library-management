"""Borrowing endpoints — issue books, return books, track overdue."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.borrowing import BorrowRequest, BorrowResponse
from app.schemas.common import PaginatedResponse
from app.services import borrowing_service

router = APIRouter(prefix="/borrowing", tags=["borrowing"])


@router.post("/issue", response_model=BorrowResponse, status_code=201)
async def issue_book(
    data: BorrowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "librarian")),
):
    """Issue a book to a member (librarian/admin only).

    Validates: book availability, member status, borrow limits, duplicate checkout.
    """
    return await borrowing_service.issue_book(
        db,
        book_id=data.book_id,
        member_id=data.member_id,
        issued_by=current_user.id,
    )


@router.post("/return/{record_id}", response_model=BorrowResponse)
async def return_book(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "librarian")),
):
    """Process a book return (librarian/admin only)."""
    return await borrowing_service.return_book(db, record_id)


@router.get("/overdue", response_model=PaginatedResponse[BorrowResponse])
async def list_overdue(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "librarian")),
):
    """List all overdue borrow records (librarian/admin only)."""
    return await borrowing_service.get_overdue_records(db, page=page, size=size)


@router.get("/history", response_model=PaginatedResponse[BorrowResponse])
async def borrow_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    member_id: uuid.UUID | None = Query(None),
    book_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, description="Filter: borrowed | returned | overdue"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """View borrow history with optional filters."""
    return await borrowing_service.get_borrow_history(
        db,
        page=page,
        size=size,
        member_id=member_id,
        book_id=book_id,
        status_filter=status,
    )
