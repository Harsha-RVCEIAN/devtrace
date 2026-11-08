
"""
env.py

Purpose:
    Configure Alembic to manage SQLAlchemy models and PostgreSQL objects.

Input:
    Database credentials from the project's .env file.
    SQLAlchemy model metadata and Alembic-utils object definitions.

Output:
    Database migration execution and schema updates.

Responsibilities:
    - Load database connection settings.
    - Configure Alembic and SQLAlchemy.
    - Register PostgreSQL views and functions for autogeneration.
    - Support offline SQL generation.
    - Execute migrations against PostgreSQL.
"""

import os
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, pool

from alembic_utils.replaceable_entity import register_entities
from app.db.base import Base
from app.db.database_objects import database_objects
import app.models.entities  # Register all nine models with Base.metadata

# Register custom PostgreSQL views and functions for Alembic autogeneration.
register_entities(database_objects)

# Load database credentials from the project-root .env file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

test_database_url = os.getenv("DEVTRACE_TEST_DATABASE_URL")
if test_database_url:
    database_url = test_database_url
else:
    from app.db.session import DATABASE_URL

    database_url = DATABASE_URL

# Safety guard: never allow the test URL to target the development database.
if test_database_url:
    from sqlalchemy.engine import make_url

    target_database = make_url(database_url).database
    if target_database != "devtrace_test_db":
        raise RuntimeError(
            f"Refusing test migration: unexpected database {target_database!r}"
        )

# Read Alembic configuration.
config = context.config

# Configure logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Register SQLAlchemy models.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without a live database connection."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to PostgreSQL and execute database migrations."""
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
