"""Tests for category endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, User
from app.schemas.auth import UserCreate
from app.schemas.category import CategoryCreate
from app.services import auth_service, category_service


class TestCategories:
    """Category endpoint tests."""

    @pytest.fixture
    async def admin_user(self, db_session: AsyncSession) -> User:
        """Create an admin user."""
        return await auth_service.register_user(
            db=db_session,
            data=UserCreate(
                email="admin@example.com",
                password="AdminPass123!",
                full_name="Admin User",
                role="admin",
            ),
        )

    @pytest.fixture
    async def admin_token(self, client: AsyncClient, admin_user: User):
        """Get admin JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def test_category(self, db_session: AsyncSession) -> Category:
        """Create a test category."""
        return await category_service.create_category(
            db=db_session,
            data=CategoryCreate(
                name="Test Category",
                description="Test description",
            ),
        )

    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, admin_token: str):
        """Test category creation."""
        response = await client.post(
            "/api/v1/categories/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Category",
                "description": "Category description",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Category"
        assert data["description"] == "Category description"

    @pytest.mark.asyncio
    async def test_create_category_unauthorized(self, client: AsyncClient):
        """Test create category without authorization."""
        response = await client.post(
            "/api/v1/categories/",
            json={
                "name": "New Category",
                "description": "Category description",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_category(
        self, client: AsyncClient, member_token: str, test_category: Category
    ):
        """Test retrieving a category."""
        response = await client.get(
            f"/api/v1/categories/{test_category.id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_category.id)
        assert data["name"] == test_category.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_category(self, client: AsyncClient, member_token: str):
        """Test retrieving nonexistent category."""
        response = await client.get(
            "/api/v1/categories/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_categories(
        self, client: AsyncClient, member_token: str, test_category: Category
    ):
        """Test listing categories."""
        response = await client.get(
            "/api/v1/categories/",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_update_category(
        self,
        client: AsyncClient,
        admin_token: str,
        test_category: Category,
    ):
        """Test updating a category."""
        response = await client.put(
            f"/api/v1/categories/{test_category.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Updated Category",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Category"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_category_unauthorized(self, client: AsyncClient, test_category: Category):
        """Test update category without authorization."""
        response = await client.put(
            f"/api/v1/categories/{test_category.id}",
            json={"name": "Updated Category"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_category(
        self,
        client: AsyncClient,
        admin_token: str,
        test_category: Category,
    ):
        """Test deleting a category."""
        response = await client.delete(
            f"/api/v1/categories/{test_category.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_category_unauthorized(self, client: AsyncClient, test_category: Category):
        """Test delete category without authorization."""
        response = await client.delete(f"/api/v1/categories/{test_category.id}")
        assert response.status_code == 401
