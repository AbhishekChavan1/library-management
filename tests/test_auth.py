"""Tests for authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.auth import UserCreate
from app.services import auth_service


class TestAuth:
    """Authentication endpoint tests."""

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession) -> User:
        """Create a test user."""
        return await auth_service.register_user(
            db=db_session,
            data=UserCreate(
                email="test@example.com",
                password="TestPassword123!",
                full_name="Test User",
            ),
        )

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient, db_session: AsyncSession):
        """Test user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration fails with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession
    ):
        """Test getting current user info."""
        # First login to get token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test get current user without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test get current user with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401
