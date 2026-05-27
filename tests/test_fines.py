"""Tests for fine/penalty endpoints."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, BorrowRecord, Member, User
from app.schemas.auth import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.category import CategoryCreate
from app.schemas.fine import FineCreate
from app.schemas.member import MemberCreate
from app.services import (
    auth_service,
    author_service,
    book_service,
    borrowing_service,
    category_service,
    fine_service,
    member_service,
)


class TestFines:
    """Fine/Penalty endpoint tests."""

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
    async def admin_token(self, client: AsyncClient, admin_user: User):
        """Get admin JWT token."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"},
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

    @pytest.fixture
    async def overdue_borrow(
        self,
        db_session: AsyncSession,
        test_book: Book,
        test_member: Member,
        librarian_user: User,
    ) -> BorrowRecord:
        """Create an overdue borrow record."""
        return await borrowing_service.issue_book(
            db=db_session,
            book_id=test_book.id,
            member_id=test_member.id,
            issued_by=librarian_user.id,
        )

    @pytest.mark.asyncio
    async def test_create_fine(
        self,
        client: AsyncClient,
        librarian_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
    ):
        """Test creating a fine."""
        response = await client.post(
            "/api/v1/fines/",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "borrow_record_id": str(overdue_borrow.id),
                "member_id": str(test_member.id),
                "amount": "5.50",
                "reason": "Overdue book",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["borrow_record_id"] == str(overdue_borrow.id)
        assert Decimal(data["amount"]) == Decimal("5.50")
        assert data["status"] == "unpaid"

    @pytest.mark.asyncio
    async def test_create_fine_unauthorized(
        self,
        client: AsyncClient,
        overdue_borrow: BorrowRecord,
        test_member: Member,
    ):
        """Test create fine without authorization."""
        response = await client.post(
            "/api/v1/fines/",
            json={
                "borrow_record_id": str(overdue_borrow.id),
                "member_id": str(test_member.id),
                "amount": "5.50",
                "reason": "Overdue book",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_duplicate_fine(
        self,
        client: AsyncClient,
        librarian_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test creating duplicate fines fails."""
        # Create first fine
        await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        # Try to create second fine
        response = await client.post(
            "/api/v1/fines/",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "borrow_record_id": str(overdue_borrow.id),
                "member_id": str(test_member.id),
                "amount": "3.00",
                "reason": "Another fine",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_fine(
        self,
        client: AsyncClient,
        librarian_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test getting a specific fine."""
        fine = await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.get(
            f"/api/v1/fines/{fine.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(fine.id)

    @pytest.mark.asyncio
    async def test_list_fines(
        self,
        client: AsyncClient,
        librarian_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test listing fines."""
        # Create a fine first
        await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.get(
            "/api/v1/fines/",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_pay_fine(
        self,
        client: AsyncClient,
        member_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test paying a fine."""
        fine = await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.post(
            f"/api/v1/fines/{fine.id}/pay",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"amount": "5.50"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        assert data["paid_at"] is not None

    @pytest.mark.asyncio
    async def test_pay_fine_partial_payment_fails(
        self,
        client: AsyncClient,
        member_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test partial fine payment fails (full payment required)."""
        fine = await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.post(
            f"/api/v1/fines/{fine.id}/pay",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"amount": "3.00"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_waive_fine(
        self,
        client: AsyncClient,
        admin_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test waiving a fine (admin only)."""
        fine = await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.post(
            f"/api/v1/fines/{fine.id}/waive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "waived"

    @pytest.mark.asyncio
    async def test_waive_fine_unauthorized(
        self,
        client: AsyncClient,
        member_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test waive fine without admin role."""
        fine = await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.post(
            f"/api/v1/fines/{fine.id}/waive",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_fines_by_member(
        self,
        client: AsyncClient,
        member_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test listing fines filtered by member."""
        await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.get(
            f"/api/v1/fines/?member_id={test_member.id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_get_member_total_fines(
        self,
        client: AsyncClient,
        member_token: str,
        test_member: Member,
        overdue_borrow: BorrowRecord,
        db_session: AsyncSession,
    ):
        """Test getting member total fines."""
        await fine_service.create_fine(
            db=db_session,
            fine_data=FineCreate(
                borrow_record_id=overdue_borrow.id,
                member_id=test_member.id,
                amount=Decimal("5.50"),
                reason="Overdue book",
            ),
        )

        response = await client.get(
            f"/api/v1/fines/member/{test_member.id}/total",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_fines" in data
        assert Decimal(data["total_fines"]) >= Decimal("5.50")

    @pytest.mark.asyncio
    async def test_fine_capped_at_max(
        self,
        client: AsyncClient,
        librarian_token: str,
        overdue_borrow: BorrowRecord,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test fine capped at MAX_FINE_PER_BOOK."""
        # Try to create a fine exceeding the max
        response = await client.post(
            "/api/v1/fines/",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "borrow_record_id": str(overdue_borrow.id),
                "member_id": str(test_member.id),
                "amount": "50.00",  # Way over the max
                "reason": "Very overdue",
            },
        )
        # Should either be capped or rejected
        if response.status_code == 201:
            data = response.json()
            # Check that amount is capped at MAX_FINE_PER_BOOK (10.00)
            assert Decimal(data["amount"]) <= Decimal("10.00")
        else:
            assert response.status_code == 400
