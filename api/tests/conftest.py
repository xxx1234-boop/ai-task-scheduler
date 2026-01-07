"""
Pytest configuration and fixtures for integration tests with Testcontainers.

This module provides:
- PostgreSQL container setup via Testcontainers
- Database migration application via Alembic
- Test session management with transaction rollback
- FastAPI test client with dependency overrides
- Factory fixtures for creating test data
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
from alembic import command
from alembic.config import Config
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer

from app.database import get_session
from app.main import app
from app.models import Genre, Project, Schedule, Setting, Task, TimeEntry


# =============================================================================
# Session-scoped fixtures (shared across all tests)
# =============================================================================


@pytest.fixture(scope="session")
def postgres_container():
    """
    Create and start a PostgreSQL 16 container for the entire test session.

    This container is reused across all tests for performance.
    Container startup takes 5-10 seconds, so reusing it significantly speeds up tests.
    """
    with PostgresContainer("postgres:16-alpine", driver="psycopg2") as postgres:
        # Wait for container to be ready
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="session")
def test_database_url(postgres_container) -> str:
    """
    Get the database URL from the Testcontainer and convert it for asyncpg.

    Testcontainers provides a psycopg2 URL, but we need to convert it to asyncpg format
    for SQLModel async operations.
    """
    # Get the connection URL (postgresql://...)
    db_url = postgres_container.get_connection_url()

    # Convert to asyncpg format (postgresql+asyncpg://...)
    async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    return async_db_url


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine connected to the test database.

    Uses NullPool to avoid connection pooling issues in tests.
    """
    engine = create_async_engine(
        test_database_url,
        echo=False,  # Set to True for SQL query debugging
        poolclass=NullPool,  # No connection pooling for tests
        future=True,
    )

    return engine


@pytest.fixture(scope="session")
def apply_migrations(test_database_url: str, postgres_container):
    """
    Apply Alembic migrations to the test database once per session.

    This runs after the container is ready and before any tests execute.
    Uses the synchronous (psycopg2) URL since Alembic migrations are synchronous.
    """
    # Get sync URL for Alembic (remove +asyncpg)
    sync_db_url = test_database_url.replace("+asyncpg", "")

    # Get the path to alembic.ini (one level up from tests/)
    alembic_ini_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "alembic.ini"
    )

    # Create Alembic config
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_db_url)

    # Run migrations to head
    command.upgrade(alembic_cfg, "head")

    yield

    # Optional: Downgrade after all tests (usually not needed)
    # command.downgrade(alembic_cfg, "base")


# =============================================================================
# Function-scoped fixtures (fresh for each test)
# =============================================================================


@pytest.fixture
async def test_session(
    test_engine: AsyncEngine, apply_migrations
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for a single test with transaction rollback.

    Each test runs in its own transaction which is rolled back after the test completes.
    This ensures perfect isolation between tests without needing to truncate tables.

    Flow:
    1. Create a connection from the engine
    2. Start a transaction
    3. Create a session bound to this transaction
    4. Yield session to the test
    5. Rollback the transaction (undoes all changes)
    6. Close the connection
    """
    # Create a connection
    connection = await test_engine.connect()

    # Start a transaction
    transaction = await connection.begin()

    # Create a session bound to this transaction
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,  # Don't expire objects after commit
        autoflush=True,
        autocommit=False,
    )

    try:
        yield session
    finally:
        # Rollback the transaction (undoes all changes made in this test)
        await transaction.rollback()

        # Close the session and connection
        await session.close()
        await connection.close()


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for testing FastAPI endpoints.

    This client has the database session dependency overridden to use the test session,
    ensuring all API calls use the same transaction as direct database operations in tests.
    """

    # Override the get_session dependency to use our test session
    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    # Create async client
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clear dependency overrides after test
    app.dependency_overrides.clear()


# =============================================================================
# Factory fixtures for creating test data
# =============================================================================


@pytest.fixture
async def genre_factory(test_session: AsyncSession):
    """
    Factory fixture for creating Genre instances in the test database.

    Usage:
        genre = await genre_factory(name="リサーチ", color="#4A90D9")
    """

    async def _create_genre(**kwargs) -> Genre:
        # Set defaults if not provided
        defaults = {
            "name": "テストジャンル",
            "color": "#000000",
        }
        defaults.update(kwargs)

        genre = Genre(**defaults)
        test_session.add(genre)
        await test_session.commit()
        await test_session.refresh(genre)
        return genre

    return _create_genre


@pytest.fixture
async def project_factory(test_session: AsyncSession):
    """
    Factory fixture for creating Project instances in the test database.

    Usage:
        project = await project_factory(name="研究プロジェクト", is_active=True)
    """

    async def _create_project(**kwargs) -> Project:
        defaults = {
            "name": "テストプロジェクト",
            "description": "テスト用のプロジェクトです",
            "is_active": True,
        }
        defaults.update(kwargs)

        project = Project(**defaults)
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)
        return project

    return _create_project


@pytest.fixture
async def task_factory(test_session: AsyncSession):
    """
    Factory fixture for creating Task instances in the test database.

    Usage:
        task = await task_factory(name="タスク1", project_id=project.id)
    """

    async def _create_task(**kwargs) -> Task:
        defaults = {
            "name": "テストタスク",
            "status": "todo",
            "priority": "中",
            "want_level": "中",
            "recurrence": "なし",
        }
        defaults.update(kwargs)

        task = Task(**defaults)
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        return task

    return _create_task


@pytest.fixture
async def schedule_factory(test_session: AsyncSession):
    """
    Factory fixture for creating Schedule instances in the test database.

    Usage:
        schedule = await schedule_factory(task_id=task.id, scheduled_date=datetime.now())
    """
    from datetime import datetime
    from decimal import Decimal

    async def _create_schedule(**kwargs) -> Schedule:
        defaults = {
            "scheduled_date": datetime.now(),
            "allocated_hours": Decimal("2.0"),
            "is_generated_by_ai": False,
        }
        defaults.update(kwargs)

        schedule = Schedule(**defaults)
        test_session.add(schedule)
        await test_session.commit()
        await test_session.refresh(schedule)
        return schedule

    return _create_schedule


@pytest.fixture
async def time_entry_factory(test_session: AsyncSession):
    """
    Factory fixture for creating TimeEntry instances in the test database.

    Usage:
        entry = await time_entry_factory(task_id=task.id, start_time=datetime.now())
    """
    from datetime import datetime

    async def _create_time_entry(**kwargs) -> TimeEntry:
        defaults = {
            "start_time": datetime.now(),
        }
        defaults.update(kwargs)

        time_entry = TimeEntry(**defaults)
        test_session.add(time_entry)
        await test_session.commit()
        await test_session.refresh(time_entry)
        return time_entry

    return _create_time_entry


@pytest.fixture
async def setting_factory(test_session: AsyncSession):
    """
    Factory fixture for creating Setting instances in the test database.

    Usage:
        setting = await setting_factory(key="max_hours", value='{"hours": 8}')
    """

    async def _create_setting(**kwargs) -> Setting:
        defaults = {
            "key": "test_setting",
            "value": "{}",
        }
        defaults.update(kwargs)

        setting = Setting(**defaults)
        test_session.add(setting)
        await test_session.commit()
        await test_session.refresh(setting)
        return setting

    return _create_setting


# =============================================================================
# Event loop configuration for async tests
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.

    This is needed for pytest-asyncio to work properly with session-scoped async fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
