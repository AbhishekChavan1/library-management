"""Author service — CRUD operations for authors."""

import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author
from app.schemas.author import AuthorCreate, AuthorResponse, AuthorUpdate
from app.schemas.common import PaginatedResponse


async def create_author(db: AsyncSession, data: AuthorCreate) -> AuthorResponse:
    """Create a new author."""
    author = Author(name=data.name, bio=data.bio)
    db.add(author)
    await db.flush()
    await db.refresh(author)
    return _to_response(author)


async def get_authors(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
) -> PaginatedResponse[AuthorResponse]:
    """List authors with optional name search and pagination."""
    query = select(Author)
    count_query = select(func.count(Author.id))

    if search:
        query = query.where(Author.name.ilike(f"%{search}%"))
        count_query = count_query.where(Author.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Author.name)
    result = await db.execute(query)
    authors = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(a) for a in authors],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def get_author(db: AsyncSession, author_id: uuid.UUID) -> AuthorResponse:
    """Get a single author by ID."""
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    return _to_response(author)


async def update_author(
    db: AsyncSession, author_id: uuid.UUID, data: AuthorUpdate
) -> AuthorResponse:
    """Update an author's details."""
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(author, field, value)

    await db.flush()
    await db.refresh(author)
    return _to_response(author)


async def delete_author(db: AsyncSession, author_id: uuid.UUID) -> None:
    """Delete an author. Raises 404 if not found."""
    result = await db.execute(select(Author).where(Author.id == author_id))
    author = result.scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Author not found")
    await db.delete(author)


def _to_response(author: Author) -> AuthorResponse:
    return AuthorResponse(
        id=author.id,
        name=author.name,
        bio=author.bio,
        created_at=author.created_at,
        book_count=len(author.books) if author.books else 0,
    )
