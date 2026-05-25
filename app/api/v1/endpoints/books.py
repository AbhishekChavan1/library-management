"""Book endpoints — CRUD with search and filtering."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.book import BookCreate, BookResponse, BookUpdate
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services import book_service

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/", response_model=PaginatedResponse[BookResponse])
async def list_books(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by title or ISBN"),
    author_id: uuid.UUID | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    available_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List books with search, filtering, and pagination."""
    return await book_service.get_books(
        db,
        page=page,
        size=size,
        search=search,
        author_id=author_id,
        category_id=category_id,
        available_only=available_only,
    )


@router.post(
    "/",
    response_model=BookResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def create_book(data: BookCreate, db: AsyncSession = Depends(get_db)):
    """Create a new book (admin/librarian only)."""
    return await book_service.create_book(db, data)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get book details by ID."""
    return await book_service.get_book(db, book_id)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def update_book(
    book_id: uuid.UUID,
    data: BookUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a book (admin/librarian only)."""
    return await book_service.update_book(db, book_id, data)


@router.delete(
    "/{book_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a book (admin only)."""
    await book_service.delete_book(db, book_id)
    return MessageResponse(message="Book deleted successfully")
