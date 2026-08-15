"""
FinPilot AI — Test Fixtures
───────────────────────────
Shared fixtures for async SQLAlchemy + httpx testing against a
PostgreSQL test database (or SQLite in-memory fallback for CI speed).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.database import Base
from app.main import app
from app.models.business import Business, User
from app.services.auth_service import hash_password, create_token

# ── Test database URL ─────────────────────────────────────────────
# Uses SQLite in-memory for fast, dependency-free test runs.
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


# ── Engine & session factory (module-scoped) ──────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine and set up all tables."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Yield a transactional session that rolls back after each test."""
    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


# ── Override FastAPI dependencies ─────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session):
    """Async test client with DB dependency overridden."""
    from app.api.deps import get_db

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Domain object factories ───────────────────────────────────────

@pytest_asyncio.fixture
async def test_business(db_session) -> Business:
    """Create and return a test business."""
    biz = Business(
        name="Test Business Ltd",
        currency="TZS",
        country="TZ",
    )
    db_session.add(biz)
    await db_session.flush()
    return biz


@pytest_asyncio.fixture
async def test_user(db_session, test_business) -> User:
    """Create and return a test user linked to the test business."""
    user = User(
        business_id=test_business.id,
        email="test@finpilot.co.tz",
        hashed_password=hash_password("TestPass123!"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user) -> dict[str, str]:
    """Return authorization headers with a valid access token."""
    token = create_token(test_user.id, "access")
    return {"Authorization": f"Bearer {token}"}
