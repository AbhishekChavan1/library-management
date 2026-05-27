"""Tests for borrowing endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, Member, User
from app.schemas.auth import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate, BookUpdate
from app.schemas.category import CategoryCreate
from app.schemas.member import MemberCreate
from app.services import (
    auth_service,
    author_service,
    book_service,
    borrowing_service,
    category_service,
    member_service,
)


class TestBorrowing:
    """Borrowing endpoint tests."""

    @pytest.fixture
    async def librarian_user(self, db_session: AsyncSession) -> User:
        """Create a librarian user."""
        return await auth_service.register_user(
            db=db_session,
            data=UserCreate(
                email="librarian@example.com",
                password="LibrarianPass123!",
                full_name="Librarian User",
                role="librarian",
            ),
        )

    @pytest.fixture
    async def librarian_token(self, client: AsyncClient, librarian_user: User):
        """Get librarian JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "librarian@example.com", "password": "LibrarianPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def member_user(self, db_session: AsyncSession) -> User:
        """Create a member user."""
        return await auth_service.register_user(
            db=db_session,
            data=UserCreate(
                email="member@example.com",
                password="MemberPass123!",
                full_name="Member User",
                role="member",
            ),
        )

    @pytest.fixture
    async def member_token(self, client: AsyncClient, member_user: User):
        """Get member JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "MemberPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def test_member(self, db_session: AsyncSession, member_user: User) -> Member:
        """Create a member."""
        return await member_service.create_member(
            db=db_session,
            data=MemberCreate(
                name="John Doe",
                email="john@example.com",
                phone="555-0123",
                membership_type="standard",
            ),
        )

    @pytest.fixture
    async def test_book(self, db_session: AsyncSession) -> Book:
        """Create a test book."""
        author = await author_service.create_author(
            db=db_session,
            data=AuthorCreate(
                name="Author Name",
                bio="Bio",
            ),
        )
        category = await category_service.create_category(
            db=db_session,
            data=CategoryCreate(
                name="Fiction",
                description="Desc",
            ),
        )
        return await book_service.create_book(
            db=db_session,
            data=BookCreate(
                title="Test Book",
                isbn="978-0-123456-78-9",
                author_id=author.id,
                category_id=category.id,
                total_copies=5,
            ),
        )

    @pytest.mark.asyncio
    async def test_issue_book(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_book: Book,
        test_member: Member,
    ):
        """Test issuing a book."""
        response = await client.post(
            "/api/v1/borrowing/issue",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "book_id": str(test_book.id),
                "member_id": str(test_member.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == str(test_book.id)
        assert data["member_id"] == str(test_member.id)
        assert data["status"] == "borrowed"

    @pytest.mark.asyncio
    async def test_issue_book_unauthorized(
        self,
        client: AsyncClient,
        test_book: Book,
        test_member: Member,
    ):
        """Test issue book without authorization."""
        response = await client.post(
            "/api/v1/borrowing/issue",
            json={
                "book_id": str(test_book.id),
                "member_id": str(test_member.id),
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_issue_book_not_available(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test issuing an unavailable book."""
        # First, reduce available copies to 0
        await book_service.update_book(
            db=db_session,
            book_id=test_book.id,
            data=BookUpdate(total_copies=0),
        )

        response = await client.post(
            "/api/v1/borrowing/issue",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "book_id": str(test_book.id),
                "member_id": str(test_member.id),
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_return_book(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_book: Book,
        test_member: Member,
        librarian_user: User,
        db_session: AsyncSession,
    ):
        """Test returning a book."""
        # Issue a book first
        borrow_record = await borrowing_service.issue_book(
            db=db_session,
            book_id=test_book.id,
            member_id=test_member.id,
            issued_by=librarian_user.id,
        )

        # Return the book
        response = await client.post(
            f"/api/v1/borrowing/return/{borrow_record.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "returned"

    @pytest.mark.asyncio
    async def test_get_member_borrowing_records(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
        test_book: Book,
        librarian_user: User,
        db_session: AsyncSession,
    ):
        """Test getting member borrowing records."""
        # Issue a book first
        await borrowing_service.issue_book(
            db=db_session,
            book_id=test_book.id,
            member_id=test_member.id,
            issued_by=librarian_user.id,
        )

        response = await client.get(
            f"/api/v1/borrowing/history?member_id={test_member.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_get_overdue_books(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test getting overdue books."""
        response = await client.get(
            "/api/v1/borrowing/overdue",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
