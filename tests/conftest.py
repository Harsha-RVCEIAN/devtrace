
"""Shared pytest fixtures for DevTrace integration tests.

Integration tests require a dedicated PostgreSQL test database.
Set DEVTRACE_TEST_DATABASE_URL before running them.

Example:
postgresql+psycopg://devtrace_app:YOUR_PASSWORD@localhost:5432/devtrace_test_db

Never point this variable at your development or production database.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session

# Load configuration from project-root .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _get_test_database_url() -> URL | str:
    env_url = os.getenv("DEVTRACE_TEST_DATABASE_URL", "").strip()

    if env_url:
        database_name = env_url.split("?", 1)[0].rsplit("/", 1)[-1]
        if "test" not in database_name.lower():
            pytest.fail(
                "Refusing to run integration tests: the database name must contain "
                "'test'. Use a dedicated database such as devtrace_test_db."
            )
        return env_url

    try:
        from app.core.config import settings

        return URL.create(
            drivername="postgresql+psycopg",
            username=settings.db_user,
            password=settings.db_password.get_secret_value(),
            host=settings.db_host,
            port=settings.db_port,
            database="devtrace_test_db",
        )
    except Exception:
        pytest.skip(
            "Set DEVTRACE_TEST_DATABASE_URL to a dedicated PostgreSQL test database."
        )


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(_get_test_database_url(), pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Roll back each test's transaction after the test finishes."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()
