"""Fine/Penalty endpoints — create, list, pay fines."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.fine import FineCreate, FinePayment, FineResponse
from app.services import fine_service

router = APIRouter(prefix="/fines", tags=["fines"])


@router.post("/", response_model=FineResponse, status_code=201)
async def create_fine(
    data: FineCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "librarian")),
):
    """Create a fine for a member (librarian/admin only).

    Validates: borrow record exists, member exists, no duplicate fine.
    """
    return await fine_service.create_fine(db, data)


@router.get("/", response_model=PaginatedResponse[FineResponse])
async def list_fines(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    member_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, description="Filter: unpaid | paid | waived"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List fines with optional filters."""
    return await fine_service.list_fines(
        db,
        page=page,
        size=size,
        member_id=member_id,
        status_filter=status,
    )


@router.get("/member/{member_id}/total")
async def get_member_total_fines(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get total unpaid fines for a member."""
    total = await fine_service.get_member_total_fines(db, member_id)
    return {"member_id": str(member_id), "total_fines": str(total)}


@router.get("/{fine_id}", response_model=FineResponse)
async def get_fine(
    fine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get a specific fine."""
    return await fine_service.get_fine(db, fine_id)


@router.post("/{fine_id}/pay", response_model=FineResponse)
async def pay_fine(
    fine_id: uuid.UUID,
    payment: FinePayment,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Pay a fine (full payment required for MVP)."""
    return await fine_service.pay_fine(db, fine_id, payment)


@router.post("/{fine_id}/waive", response_model=FineResponse)
async def waive_fine(
    fine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Waive a fine (admin only)."""
    return await fine_service.waive_fine(db, fine_id)
