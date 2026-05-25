"""Member service — CRUD for library members."""

import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member
from app.schemas.common import PaginatedResponse
from app.schemas.member import MemberCreate, MemberResponse, MemberUpdate


async def create_member(db: AsyncSession, data: MemberCreate) -> MemberResponse:
    """Register a new library member. Raises 409 if email already exists."""
    result = await db.execute(select(Member).where(Member.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member with this email already exists",
        )

    member = Member(
        name=data.name,
        email=data.email,
        phone=data.phone,
        membership_type=data.membership_type,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return _to_response(member)


async def get_members(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    active_only: bool = False,
) -> PaginatedResponse[MemberResponse]:
    """List members with optional search and pagination."""
    query = select(Member)
    count_query = select(func.count(Member.id))

    if search:
        search_filter = Member.name.ilike(f"%{search}%") | Member.email.ilike(
            f"%{search}%"
        ) | Member.membership_id.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    if active_only:
        query = query.where(Member.is_active.is_(True))
        count_query = count_query.where(Member.is_active.is_(True))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Member.name)
    result = await db.execute(query)
    members = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(m) for m in members],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def get_member(db: AsyncSession, member_id: uuid.UUID) -> MemberResponse:
    """Get a single member by ID."""
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )
    return _to_response(member)


async def update_member(
    db: AsyncSession, member_id: uuid.UUID, data: MemberUpdate
) -> MemberResponse:
    """Update a member's details."""
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(member, field, value)

    await db.flush()
    await db.refresh(member)
    return _to_response(member)


async def delete_member(db: AsyncSession, member_id: uuid.UUID) -> None:
    """Delete a member. Raises 404 if not found."""
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )
    await db.delete(member)


def _to_response(member: Member) -> MemberResponse:
    active_borrows = 0
    if member.borrow_records:
        active_borrows = sum(
            1 for r in member.borrow_records if r.status == "borrowed"
        )
    return MemberResponse(
        id=member.id,
        membership_id=member.membership_id,
        name=member.name,
        email=member.email,
        phone=member.phone,
        membership_type=member.membership_type,
        is_active=member.is_active,
        joined_at=member.joined_at,
        active_borrows=active_borrows,
    )
