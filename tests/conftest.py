"""Pytest configuration and fixtures for ViralForge."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from src.db.models import Base


# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_profile_data():
    """Sample Instagram profile data for tests."""
    return {
        "username": "test_profile",
        "full_name": "Test Profile",
        "follower_count": 100000,
        "nicho": "humor",
        "is_active": True,
    }


@pytest.fixture
def sample_video_data():
    """Sample video data for tests."""
    return {
        "original_url": "https://instagram.com/p/test123",
        "play_count": 500000,
        "like_count": 25000,
        "comment_count": 1500,
        "caption": "Test video caption #viral",
        "duration_seconds": 45,
    }
