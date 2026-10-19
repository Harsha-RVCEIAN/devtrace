
"""
env.py

Purpose:
    Configure Alembic to connect to the PostgreSQL database
    and manage database schema migrations.

Input:
    Database credentials from the project's .env file.
    SQLAlchemy model metadata.

Output:
    Database migration execution and schema updates.

Responsibilities:
    - Load database connection settings.
    - Configure Alembic and SQLAlchemy.
    - Support offline SQL generation.
    - Execute migrations against PostgreSQL.
    - Provide model metadata for schema change detection.
"""

import os
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, pool
from app.db.base import Base
import app.models.entities  # Registers all nine models with Base.metadata

# Load database credentials from the project-root .env file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),
    database=os.environ["DB_NAME"],
)

# Read Alembic configuration.
config = context.config

# Configure logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy model metadata will be connected here later.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without a live database connection."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to PostgreSQL and execute database migrations."""
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
