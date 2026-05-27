"""Tests for book endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, Book, Category, User
from app.schemas.auth import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.category import CategoryCreate
from app.services import auth_service, author_service, book_service, category_service


class TestBooks:
    """Book endpoint tests."""

    @pytest.fixture
    async def admin_user(self, db_session: AsyncSession) -> User:
        """Create an admin user for authorization."""
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
        """Get admin user JWT token."""
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
                name="John Doe",
                bio="A great author",
            ),
        )

    @pytest.fixture
    async def test_category(self, db_session: AsyncSession) -> Category:
        """Create a test category."""
        return await category_service.create_category(
            db=db_session,
            data=CategoryCreate(
                name="Fiction",
                description="Fictional stories",
            ),
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
            db=db_session,
            data=BookCreate(
                title="Test Book",
                isbn="978-0-123456-78-9",
                author_id=test_author.id,
                category_id=test_category.id,
                total_copies=5,
            ),
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
            "/api/v1/books/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "New Book",
                "isbn": "978-1-234567-89-0",
                "author_id": str(test_author.id),
                "category_id": str(test_category.id),
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
            "/api/v1/books/",
            json={
                "title": "New Book",
                "isbn": "978-1-234567-89-0",
                "author_id": "00000000-0000-0000-0000-000000000001",
                "category_id": "00000000-0000-0000-0000-000000000002",
                "total_copies": 3,
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_book(self, client: AsyncClient, member_token: str, test_book: Book):
        """Test retrieving a book."""
        response = await client.get(
            f"/api/v1/books/{test_book.id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_book.id)
        assert data["title"] == test_book.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_book(self, client: AsyncClient, member_token: str):
        """Test retrieving nonexistent book."""
        response = await client.get(
            "/api/v1/books/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_books(self, client: AsyncClient, member_token: str, test_book: Book):
        """Test listing books."""
        response = await client.get(
            "/api/v1/books/",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

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
            json={"total_copies": 10},
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
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_book_unauthorized(self, client: AsyncClient, test_book: Book):
        """Test delete book without authorization."""
        response = await client.delete(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_books_by_title(
        self, client: AsyncClient, member_token: str, test_book: Book
    ):
        """Test searching books by title."""
        response = await client.get(
            "/api/v1/books/",
            headers={"Authorization": f"Bearer {member_token}"},
            params={"page": 1, "size": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
