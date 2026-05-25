"""Category endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """List all categories."""
    return await category_service.get_categories(db, page=page, size=size)


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new category (admin/librarian only)."""
    return await category_service.create_category(db, data)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Get category details by ID."""
    return await category_service.get_category(db, category_id)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_role("admin", "librarian"))],
)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a category (admin/librarian only)."""
    return await category_service.update_category(db, category_id, data)


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a category (admin only)."""
    await category_service.delete_category(db, category_id)
    return MessageResponse(message="Category deleted successfully")
