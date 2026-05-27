"""Tests for borrowing endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, Member, User
from app.services.auth_service import auth_service
from app.services.author_service import author_service
from app.services.book_service import book_service
from app.services.borrowing_service import borrowing_service
from app.services.category_service import category_service
from app.services.member_service import member_service


class TestBorrowing:
    """Borrowing endpoint tests."""

    @pytest.fixture
    async def librarian_user(self, db_session: AsyncSession) -> User:
        """Create a librarian user."""
        return await auth_service.register_user(
            db_session=db_session,
            username="librarian",
            email="librarian@example.com",
            password="LibrarianPass123!",
        )

    @pytest.fixture
    async def librarian_token(self, client: AsyncClient, librarian_user: User):
        """Get librarian JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "librarian", "password": "LibrarianPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def member_user(self, db_session: AsyncSession) -> User:
        """Create a member user."""
        return await auth_service.register_user(
            db_session=db_session,
            username="member",
            email="member@example.com",
            password="MemberPass123!",
        )

    @pytest.fixture
    async def member_token(self, client: AsyncClient, member_user: User):
        """Get member JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "member", "password": "MemberPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def test_member(self, db_session: AsyncSession, member_user: User) -> Member:
        """Create a member."""
        return await member_service.create_member(
            db_session=db_session,
            user_id=member_user.id,
            first_name="John",
            last_name="Doe",
            phone="555-0123",
            address="123 Main St",
        )

    @pytest.fixture
    async def test_book(self, db_session: AsyncSession) -> Book:
        """Create a test book."""
        author = await author_service.create_author(
            db_session=db_session,
            name="Author Name",
            biography="Bio",
        )
        category = await category_service.create_category(
            db_session=db_session,
            name="Fiction",
            description="Desc",
        )
        return await book_service.create_book(
            db_session=db_session,
            title="Test Book",
            isbn="978-0-123456-78-9",
            author_id=author.id,
            category_id=category.id,
            total_copies=5,
            available_copies=5,
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
                "book_id": test_book.id,
                "member_id": test_member.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["member_id"] == test_member.id
        assert data["status"] == "active"

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
                "book_id": test_book.id,
                "member_id": test_member.id,
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
            db_session=db_session,
            book_id=test_book.id,
            total_copies=0,
            available_copies=0,
        )

        response = await client.post(
            "/api/v1/borrowing/issue",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "book_id": test_book.id,
                "member_id": test_member.id,
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
        db_session: AsyncSession,
    ):
        """Test returning a book."""
        # Issue a book first
        borrow_record = await borrowing_service.issue_book(
            db_session=db_session,
            book_id=test_book.id,
            member_id=test_member.id,
            issuer_id=1,
        )

        # Return the book
        response = await client.post(
            f"/api/v1/borrowing/{borrow_record.id}/return",
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
        db_session: AsyncSession,
    ):
        """Test getting member borrowing records."""
        # Issue a book first
        await borrowing_service.issue_book(
            db_session=db_session,
            book_id=test_book.id,
            member_id=test_member.id,
            issuer_id=1,
        )

        response = await client.get(
            f"/api/v1/borrowing/member/{test_member.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

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
        assert isinstance(data, list)
