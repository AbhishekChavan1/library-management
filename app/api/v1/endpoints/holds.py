"""Hold/Reservation endpoints — create, list, cancel, fulfill holds."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.hold import HoldCreate, HoldResponse
from app.services import hold_service

router = APIRouter(prefix="/holds", tags=["holds"])


@router.post("/", response_model=HoldResponse, status_code=201)
async def create_hold(
    data: HoldCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a hold on a book for a member.

    Validates: book exists, member exists and active, no duplicate hold.
    """
    return await hold_service.create_hold(db, data)


@router.get("/", response_model=PaginatedResponse[HoldResponse])
async def list_holds(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    member_id: uuid.UUID | None = Query(None),
    book_id: uuid.UUID | None = Query(None),
    status: str | None = Query(
        None, description="Filter: active | fulfilled | expired | cancelled"
    ),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List holds with optional filters."""
    return await hold_service.list_holds(
        db,
        page=page,
        size=size,
        member_id=member_id,
        book_id=book_id,
        status_filter=status,
    )


@router.get("/{hold_id}", response_model=HoldResponse)
async def get_hold(
    hold_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get a specific hold."""
    return await hold_service.get_hold(db, hold_id)


@router.post("/{hold_id}/cancel", response_model=HoldResponse)
async def cancel_hold(
    hold_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Cancel an active hold."""
    return await hold_service.cancel_hold(db, hold_id)


@router.post("/{hold_id}/fulfill", response_model=HoldResponse)
async def fulfill_hold(
    hold_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "librarian")),
):
    """Fulfill a hold (book ready for pickup, librarian/admin only)."""
    return await hold_service.fulfill_hold(db, hold_id)
