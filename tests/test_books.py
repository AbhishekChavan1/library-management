"""Tests for book endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, Book, Category, User
from app.services.auth_service import auth_service
from app.services.author_service import author_service
from app.services.book_service import book_service
from app.services.category_service import category_service


class TestBooks:
    """Book endpoint tests."""

    @pytest.fixture
    async def admin_user(self, db_session: AsyncSession) -> User:
        """Create an admin user for authorization."""
        return await auth_service.register_user(
            db_session=db_session,
            username="admin",
            email="admin@example.com",
            password="AdminPass123!",
        )

    @pytest.fixture
    async def admin_token(self, client: AsyncClient, admin_user: User):
        """Get admin user JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def test_author(self, db_session: AsyncSession) -> Author:
        """Create a test author."""
        return await author_service.create_author(
            db_session=db_session,
            name="John Doe",
            biography="A great author",
        )

    @pytest.fixture
    async def test_category(self, db_session: AsyncSession) -> Category:
        """Create a test category."""
        return await category_service.create_category(
            db_session=db_session,
            name="Fiction",
            description="Fictional stories",
        )

    @pytest.fixture
    async def test_book(
        self,
        db_session: AsyncSession,
        test_author: Author,
        test_category: Category,
    ) -> Book:
        """Create a test book."""
        return await book_service.create_book(
            db_session=db_session,
            title="Test Book",
            isbn="978-0-123456-78-9",
            author_id=test_author.id,
            category_id=test_category.id,
            total_copies=5,
            available_copies=5,
        )

    @pytest.mark.asyncio
    async def test_create_book(
        self,
        client: AsyncClient,
        admin_token: str,
        test_author: Author,
        test_category: Category,
    ):
        """Test book creation."""
        response = await client.post(
            "/api/v1/books",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "New Book",
                "isbn": "978-1-234567-89-0",
                "author_id": test_author.id,
                "category_id": test_category.id,
                "total_copies": 3,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Book"
        assert data["isbn"] == "978-1-234567-89-0"

    @pytest.mark.asyncio
    async def test_create_book_unauthorized(self, client: AsyncClient):
        """Test create book without authorization."""
        response = await client.post(
            "/api/v1/books",
            json={
                "title": "New Book",
                "isbn": "978-1-234567-89-0",
                "author_id": 1,
                "category_id": 1,
                "total_copies": 3,
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_book(self, client: AsyncClient, test_book: Book):
        """Test retrieving a book."""
        response = await client.get(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_book.id
        assert data["title"] == test_book.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_book(self, client: AsyncClient):
        """Test retrieving nonexistent book."""
        response = await client.get("/api/v1/books/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_books(self, client: AsyncClient, test_book: Book):
        """Test listing books."""
        response = await client.get("/api/v1/books")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_update_book(
        self,
        client: AsyncClient,
        admin_token: str,
        test_book: Book,
    ):
        """Test updating a book."""
        response = await client.put(
            f"/api/v1/books/{test_book.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"total_copies": 10, "available_copies": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_copies"] == 10

    @pytest.mark.asyncio
    async def test_delete_book(
        self,
        client: AsyncClient,
        admin_token: str,
        test_book: Book,
    ):
        """Test deleting a book."""
        response = await client.delete(
            f"/api/v1/books/{test_book.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_book_unauthorized(self, client: AsyncClient, test_book: Book):
        """Test delete book without authorization."""
        response = await client.delete(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_books_by_title(self, client: AsyncClient, test_book: Book):
        """Test searching books by title."""
        response = await client.get(
            "/api/v1/books",
            params={"skip": 0, "limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
