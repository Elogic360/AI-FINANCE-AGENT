import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.database import Base
from app.models import *  # noqa

# Use main database for tests (schema already exists from Alembic)
TEST_DATABASE_URL = "postgresql://finpilot:finpilot@localhost:5433/finpilot"

engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def verify_tables():
    """Verify tables exist before running tests."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'"))
        count = result.scalar()
        assert count >= 15, f"Expected >= 15 tables, found {count}"


@pytest.fixture
def db_session():
    """Provide a clean database session for each test."""
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()
