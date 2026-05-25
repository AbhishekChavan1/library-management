"""Member endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.member import MemberCreate, MemberResponse, MemberUpdate
from app.services import member_service

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/", response_model=PaginatedResponse[MemberResponse])
async def list_members(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by name, email, or membership ID"),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List library members with optional search."""
    return await member_service.get_members(
        db, page=page, size=size, search=search, active_only=active_only
    )


@router.post(
    "/",
    response_model=MemberResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def create_member(data: MemberCreate, db: AsyncSession = Depends(get_db)):
    """Register a new library member (admin/librarian only)."""
    return await member_service.create_member(db, data)


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get member details by ID."""
    return await member_service.get_member(db, member_id)


@router.put(
    "/{member_id}",
    response_model=MemberResponse,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def update_member(
    member_id: uuid.UUID,
    data: MemberUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a member (admin/librarian only)."""
    return await member_service.update_member(db, member_id, data)


@router.delete(
    "/{member_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_member(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a member (admin only)."""
    await member_service.delete_member(db, member_id)
    return MessageResponse(message="Member deleted successfully")
