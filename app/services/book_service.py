"""Book service — CRUD, search, and filtering for books."""

import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.schemas.book import BookCreate, BookResponse, BookUpdate
from app.schemas.common import PaginatedResponse


async def create_book(db: AsyncSession, data: BookCreate) -> BookResponse:
    """Create a new book. Raises 409 if ISBN already exists."""
    result = await db.execute(select(Book).where(Book.isbn == data.isbn))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Book with ISBN '{data.isbn}' already exists",
        )

    book = Book(
        isbn=data.isbn,
        title=data.title,
        author_id=data.author_id,
        category_id=data.category_id,
        total_copies=data.total_copies,
        available_copies=data.total_copies,  # all copies available initially
        year_published=data.year_published,
        description=data.description,
    )
    db.add(book)
    await db.flush()
    await db.refresh(book)
    return _to_response(book)


async def get_books(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    author_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    available_only: bool = False,
) -> PaginatedResponse[BookResponse]:
    """List books with search, filters, and pagination."""
    query = select(Book)
    count_query = select(func.count(Book.id))

    # Apply filters
    if search:
        search_filter = Book.title.ilike(f"%{search}%") | Book.isbn.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    if author_id:
        query = query.where(Book.author_id == author_id)
        count_query = count_query.where(Book.author_id == author_id)
    if category_id:
        query = query.where(Book.category_id == category_id)
        count_query = count_query.where(Book.category_id == category_id)
    if available_only:
        query = query.where(Book.available_copies > 0)
        count_query = count_query.where(Book.available_copies > 0)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Book.title)
    result = await db.execute(query)
    books = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(b) for b in books],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def get_book(db: AsyncSession, book_id: uuid.UUID) -> BookResponse:
    """Get a single book by ID."""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return _to_response(book)


async def update_book(
    db: AsyncSession, book_id: uuid.UUID, data: BookUpdate
) -> BookResponse:
    """Update a book's details."""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    update_data = data.model_dump(exclude_unset=True)

    # If total_copies changed, adjust available_copies proportionally
    if "total_copies" in update_data:
        diff = update_data["total_copies"] - book.total_copies
        book.available_copies = max(0, book.available_copies + diff)

    for field, value in update_data.items():
        setattr(book, field, value)

    await db.flush()
    await db.refresh(book)
    return _to_response(book)


async def delete_book(db: AsyncSession, book_id: uuid.UUID) -> None:
    """Delete a book. Raises 404 if not found."""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    await db.delete(book)


def _to_response(book: Book) -> BookResponse:
    return BookResponse(
        id=book.id,
        isbn=book.isbn,
        title=book.title,
        author_id=book.author_id,
        author_name=book.author.name if book.author else None,
        category_id=book.category_id,
        category_name=book.category.name if book.category else None,
        total_copies=book.total_copies,
        available_copies=book.available_copies,
        year_published=book.year_published,
        description=book.description,
        created_at=book.created_at,
    )
