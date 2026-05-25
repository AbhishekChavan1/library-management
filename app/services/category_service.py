"""Category service — CRUD operations for book categories."""

import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import PaginatedResponse


async def create_category(db: AsyncSession, data: CategoryCreate) -> CategoryResponse:
    """Create a new category. Raises 409 if name already exists."""
    result = await db.execute(select(Category).where(Category.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{data.name}' already exists",
        )

    category = Category(name=data.name, description=data.description)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return _to_response(category)


async def get_categories(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse[CategoryResponse]:
    """List all categories with pagination."""
    total = (await db.execute(select(func.count(Category.id)))).scalar() or 0
    result = await db.execute(
        select(Category).offset((page - 1) * size).limit(size).order_by(Category.name)
    )
    categories = result.scalars().all()

    return PaginatedResponse(
        items=[_to_response(c) for c in categories],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


async def get_category(db: AsyncSession, category_id: uuid.UUID) -> CategoryResponse:
    """Get a single category by ID."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return _to_response(category)


async def update_category(
    db: AsyncSession, category_id: uuid.UUID, data: CategoryUpdate
) -> CategoryResponse:
    """Update a category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)
    return _to_response(category)


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> None:
    """Delete a category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    await db.delete(category)


def _to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        book_count=len(category.books) if category.books else 0,
    )
