"""Tests for member endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member, User
from app.services.auth_service import auth_service
from app.services.member_service import member_service


class TestMembers:
    """Member endpoint tests."""

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
    async def test_member(self, db_session: AsyncSession, librarian_user: User) -> Member:
        """Create a test member."""
        return await member_service.create_member(
            db_session=db_session,
            user_id=librarian_user.id,
            first_name="John",
            last_name="Doe",
            phone="555-0123",
            address="123 Main St",
        )

    @pytest.mark.asyncio
    async def test_register_member(self, client: AsyncClient, db_session: AsyncSession):
        """Test member registration."""
        # Create a user first
        user = await auth_service.register_user(
            db_session=db_session,
            username="newmember",
            email="newmember@example.com",
            password="MemberPass123!",
        )

        response = await client.post(
            "/api/v1/members/register",
            json={
                "user_id": user.id,
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "555-0124",
                "address": "456 Oak Ave",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_get_member(self, client: AsyncClient, test_member: Member):
        """Test retrieving a member."""
        response = await client.get(f"/api/v1/members/{test_member.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_member.id
        assert data["first_name"] == test_member.first_name

    @pytest.mark.asyncio
    async def test_get_nonexistent_member(self, client: AsyncClient):
        """Test retrieving nonexistent member."""
        response = await client.get("/api/v1/members/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_members(self, client: AsyncClient, test_member: Member):
        """Test listing members."""
        response = await client.get("/api/v1/members")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_update_member(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
    ):
        """Test updating a member."""
        response = await client.put(
            f"/api/v1/members/{test_member.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={"phone": "555-9999", "address": "789 Pine Rd"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "555-9999"
        assert data["address"] == "789 Pine Rd"

    @pytest.mark.asyncio
    async def test_member_status(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
    ):
        """Test getting member status."""
        response = await client.get(
            f"/api/v1/members/{test_member.id}/status",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "active_borrowings" in data

    @pytest.mark.asyncio
    async def test_suspend_member(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
    ):
        """Test suspending a member."""
        response = await client.post(
            f"/api/v1/members/{test_member.id}/suspend",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={"reason": "Non-payment of fines"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_suspended"] is True

    @pytest.mark.asyncio
    async def test_suspend_member_unauthorized(self, client: AsyncClient, test_member: Member):
        """Test suspend member without authorization."""
        response = await client.post(
            f"/api/v1/members/{test_member.id}/suspend",
            json={"reason": "Non-payment of fines"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reactivate_member(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test reactivating a suspended member."""
        # First suspend the member
        await member_service.suspend_member(
            db_session=db_session,
            member_id=test_member.id,
            reason="Test suspension",
        )

        response = await client.post(
            f"/api/v1/members/{test_member.id}/reactivate",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_suspended"] is False
