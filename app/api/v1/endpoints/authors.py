"""Author endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.author import AuthorCreate, AuthorResponse, AuthorUpdate
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services import author_service

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/", response_model=PaginatedResponse[AuthorResponse])
async def list_authors(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by author name"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List authors with optional search."""
    return await author_service.get_authors(db, page=page, size=size, search=search)


@router.post(
    "/",
    response_model=AuthorResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def create_author(data: AuthorCreate, db: AsyncSession = Depends(get_db)):
    """Create a new author (admin/librarian only)."""
    return await author_service.create_author(db, data)


@router.get("/{author_id}", response_model=AuthorResponse)
async def get_author(
    author_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get author details by ID."""
    return await author_service.get_author(db, author_id)


@router.put(
    "/{author_id}",
    response_model=AuthorResponse,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def update_author(
    author_id: uuid.UUID,
    data: AuthorUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an author (admin/librarian only)."""
    return await author_service.update_author(db, author_id, data)


@router.delete(
    "/{author_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_author(
    author_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an author (admin only)."""
    await author_service.delete_author(db, author_id)
    return MessageResponse(message="Author deleted successfully")
