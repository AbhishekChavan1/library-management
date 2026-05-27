from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.schemas.auth import UserCreate
from app.services.auth_service import register_user


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test engine with session scope."""
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def setup_database(test_engine):
    """Setup and teardown database for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine, setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session for tests."""
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")
        yield session
        await transaction.rollback()


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession) -> User:
    """Create a common member user for authenticated tests."""
    return await register_user(
        db=db_session,
        data=UserCreate(
            email="testmember@example.com",
            password="TestMemberPass123!",
            full_name="Test Member",
            role="member",
        ),
    )


@pytest_asyncio.fixture
async def member_token(client: AsyncClient, member_user: User) -> str:
    """Get member JWT token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testmember@example.com", "password": "TestMemberPass123!"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
