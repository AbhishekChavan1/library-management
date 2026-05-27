"""Tests for author endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, User
from app.schemas.auth import UserCreate
from app.schemas.author import AuthorCreate
from app.services import auth_service, author_service


class TestAuthors:
    """Author endpoint tests."""

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
    async def test_author(self, db_session: AsyncSession) -> Author:
        """Create a test author."""
        return await author_service.create_author(
            db=db_session,
            data=AuthorCreate(
                name="Test Author",
                bio="Test biography",
            ),
        )

    @pytest.mark.asyncio
    async def test_create_author(self, client: AsyncClient, admin_token: str):
        """Test author creation."""
        response = await client.post(
            "/api/v1/authors/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "New Author",
                "bio": "Author biography",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Author"
        assert data["bio"] == "Author biography"

    @pytest.mark.asyncio
    async def test_create_author_unauthorized(self, client: AsyncClient):
        """Test create author without authorization."""
        response = await client.post(
            "/api/v1/authors/",
            json={
                "name": "New Author",
                "bio": "Author biography",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_author(self, client: AsyncClient, member_token: str, test_author: Author):
        """Test retrieving an author."""
        response = await client.get(
            f"/api/v1/authors/{test_author.id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_author.id)
        assert data["name"] == test_author.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_author(self, client: AsyncClient, member_token: str):
        """Test retrieving nonexistent author."""
        response = await client.get(
            "/api/v1/authors/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_authors(self, client: AsyncClient, member_token: str, test_author: Author):
        """Test listing authors."""
        response = await client.get(
            "/api/v1/authors/",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_update_author(
        self,
        client: AsyncClient,
        admin_token: str,
        test_author: Author,
    ):
        """Test updating an author."""
        response = await client.put(
            f"/api/v1/authors/{test_author.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Updated Author", "bio": "Updated bio"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Author"
        assert data["bio"] == "Updated bio"

    @pytest.mark.asyncio
    async def test_update_author_unauthorized(self, client: AsyncClient, test_author: Author):
        """Test update author without authorization."""
        response = await client.put(
            f"/api/v1/authors/{test_author.id}",
            json={"name": "Updated Author"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_author(
        self,
        client: AsyncClient,
        admin_token: str,
        test_author: Author,
    ):
        """Test deleting an author."""
        response = await client.delete(
            f"/api/v1/authors/{test_author.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_author_unauthorized(self, client: AsyncClient, test_author: Author):
        """Test delete author without authorization."""
        response = await client.delete(f"/api/v1/authors/{test_author.id}")
        assert response.status_code == 401
