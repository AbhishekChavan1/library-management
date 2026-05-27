"""Tests for member endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member, User
from app.schemas.auth import UserCreate
from app.schemas.member import MemberCreate
from app.services import auth_service, member_service


class TestMembers:
    """Member endpoint tests."""

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
    async def test_member(self, db_session: AsyncSession) -> Member:
        """Create a test member."""
        return await member_service.create_member(
            db=db_session,
            data=MemberCreate(
                name="John Doe",
                email="john@example.com",
                phone="555-0123",
                membership_type="standard",
            ),
        )

    @pytest.mark.asyncio
    async def test_create_member(self, client: AsyncClient, librarian_token: str):
        """Test member creation."""
        response = await client.post(
            "/api/v1/members/",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0124",
                "membership_type": "premium",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Jane Smith"
        assert data["email"] == "jane@example.com"

    @pytest.mark.asyncio
    async def test_create_member_unauthorized(self, client: AsyncClient):
        """Test create member without authorization."""
        response = await client.post(
            "/api/v1/members/",
            json={
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "555-0124",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_duplicate_member(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
    ):
        """Test creating a duplicate member (same email) fails."""
        response = await client.post(
            "/api/v1/members/",
            headers={"Authorization": f"Bearer {librarian_token}"},
            json={
                "name": "John Doe Copy",
                "email": "john@example.com",  # Same email as test_member
                "phone": "555-9999",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_member(self, client: AsyncClient, librarian_token: str, test_member: Member):
        """Test retrieving a member."""
        response = await client.get(
            f"/api/v1/members/{test_member.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_member.id)
        assert data["name"] == test_member.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_member(self, client: AsyncClient, librarian_token: str):
        """Test retrieving nonexistent member."""
        response = await client.get(
            "/api/v1/members/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_members(
        self, client: AsyncClient, librarian_token: str, test_member: Member
    ):
        """Test listing members."""
        response = await client.get(
            "/api/v1/members/",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

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
            json={"phone": "555-9999", "name": "John Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "555-9999"
        assert data["name"] == "John Updated"

    @pytest.mark.asyncio
    async def test_update_member_unauthorized(self, client: AsyncClient, test_member: Member):
        """Test update member without authorization."""
        response = await client.put(
            f"/api/v1/members/{test_member.id}",
            json={"phone": "555-9999"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_member(
        self,
        client: AsyncClient,
        admin_token: str,
        test_member: Member,
        db_session: AsyncSession,
    ):
        """Test deleting a member."""
        response = await client.delete(
            f"/api/v1/members/{test_member.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_delete_member_unauthorized(self, client: AsyncClient, test_member: Member):
        """Test delete member without authorization."""
        response = await client.delete(f"/api/v1/members/{test_member.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_member_forbidden(
        self,
        client: AsyncClient,
        librarian_token: str,
        test_member: Member,
    ):
        """Test delete member without admin role."""
        response = await client.delete(
            f"/api/v1/members/{test_member.id}",
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert response.status_code == 403
