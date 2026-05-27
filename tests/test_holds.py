"""Tests for hold/reservation endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, Member, User
from app.schemas.auth import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.category import CategoryCreate
from app.schemas.hold import HoldCreate
from app.schemas.member import MemberCreate
from app.services import (
    auth_service,
    author_service,
    book_service,
    category_service,
    hold_service,
    member_service,
)


class TestHolds:
    """Hold/Reservation endpoint tests."""

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
    async def member_token(self, client: AsyncClient, member_user: User):
        """Get member JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "MemberPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def librarian_token(self, client: AsyncClient, librarian_user: User):
        """Get librarian JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "librarian@example.com", "password": "LibrarianPass123!"},
        )
        return response.json()["access_token"]

    @pytest.fixture
    async def test_member(self, db_session: AsyncSession) -> Member:
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
    async def test_create_hold(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
    ):
        """Test creating a hold."""
        response = await client.post(
            "/api/v1/holds/",
            headers={"Authorization": f"Bearer {member_token}"},
            json={
                "book_id": str(test_book.id),
                "member_id": str(test_member.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == str(test_book.id)
        assert data["member_id"] == str(test_member.id)
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_hold_unauthorized(
        self,
        client: AsyncClient,
        test_book: Book,
        test_member: Member,
    ):
        """Test create hold without authorization."""
        response = await client.post(
            "/api/v1/holds/",
            json={
                "book_id": str(test_book.id),
                "member_id": str(test_member.id),
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_duplicate_hold(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test creating duplicate holds fails."""
        # Create first hold
        await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        # Try to create second hold
        response = await client.post(
            "/api/v1/holds/",
            headers={"Authorization": f"Bearer {member_token}"},
            json={
                "book_id": str(test_book.id),
                "member_id": str(test_member.id),
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_hold(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test getting a specific hold."""
        hold = await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        response = await client.get(
            f"/api/v1/holds/{hold.id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(hold.id)

    @pytest.mark.asyncio
    async def test_list_holds(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test listing holds."""
        # Create a hold first
        await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        response = await client.get(
            "/api/v1/holds/",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_cancel_hold(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test canceling a hold."""
        hold = await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        response = await client.post(
            f"/api/v1/holds/{hold.id}/cancel",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_fulfill_hold(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test fulfilling a hold (librarian only)."""
        hold = await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        response = await client.post(
            f"/api/v1/holds/{hold.id}/fulfill",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fulfilled"
        assert data["fulfilled_date"] is not None

    @pytest.mark.asyncio
    async def test_fulfill_hold_unauthorized(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test fulfill hold without librarian role."""
        hold = await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        response = await client.post(
            f"/api/v1/holds/{hold.id}/fulfill",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_holds_by_member(
        self,
        client: AsyncClient,
        member_token: str,
        test_book: Book,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test listing holds filtered by member."""
        await hold_service.create_hold(
            db=db_session,
            hold_data=HoldCreate(
                book_id=test_book.id,
                member_id=test_member.id,
            ),
        )

        response = await client.get(
            f"/api/v1/holds/?member_id={test_member.id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        assert data["items"][0]["member_id"] == str(test_member.id)
