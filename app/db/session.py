
"""
DevTrace database connection and session management.

This module creates the SQLAlchemy engine used to communicate with PostgreSQL,
defines a reusable session factory, and provides a FastAPI dependency for
request-scoped database sessions.

The engine manages database connections and connection pooling. SessionLocal
creates individual SQLAlchemy sessions for database operations. get_db()
provides a session to an API request and guarantees that it is closed afterward.

Transactions are controlled by the service or endpoint performing the
operation. This dependency does not automatically commit successful requests:
services must commit explicitly and roll back failed transactions.
Alembic remains responsible for creating and updating the database schema.
"""

from collections.abc import Generator

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Reuse the validated configuration defined by the application.
# The password is stored as SecretStr and must be explicitly unwrapped when
# constructing the connection URL.
from app.core.config import settings


# Build the PostgreSQL connection URL from individual components instead of
# concatenating a string. URL.create() safely handles special characters in
# usernames and passwords.
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=settings.db_user,
    password=settings.db_password.get_secret_value(),
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
)


# Create the SQLAlchemy engine.
#
# The engine is shared across the application; it does not create a new
# connection for every request. SQLAlchemy manages a pool of reusable
# connections and opens connections when database operations require them.
#
# pool_pre_ping checks a pooled connection before using it, helping SQLAlchemy
# detect connections that have become invalid.
#
# pool_size sets the number of persistent pooled connections.
# max_overflow permits temporary additional connections during high demand.
# pool_timeout limits how long a request waits for a connection from the pool.
engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)


# Create a factory for database sessions.
#
# Each call to SessionLocal() returns a new Session associated with the engine.
#
# autoflush=False prevents pending ORM changes from being flushed automatically
# before every query; code can explicitly flush when it needs database-generated
# values before committing.
#
# expire_on_commit=False keeps already-loaded ORM attributes accessible after
# a commit without automatically expiring them.
#
# A Session is not safe to share concurrently between multiple requests or
# threads. Each request must receive its own session.
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Provide one database session for a FastAPI dependency.

    The session is created when the dependency is entered and closed in the
    finally block, including when the endpoint raises an exception.

    If an exception is thrown through the dependency, roll back the current
    transaction before closing the session. Successful transactions are not
    committed automatically; the service that owns the operation must commit.
    """
    # Create a new session for this request instead of sharing a global session.
    db = SessionLocal()

    try:
        # Yield the session to the endpoint or service that requested it.
        yield db

    except Exception:
        # Discard pending transactional changes when an error propagates
        # through this dependency. The exception is re-raised automatically.
        db.rollback()
        raise

    finally:
        # Release the session's resources. Any uncommitted transaction is
        # rolled back by SQLAlchemy when the session is closed.
        db.close()


def check_database_connection() -> bool:
    """
    Check whether PostgreSQL can execute a simple query.

    This helper can be used by a database-aware health check or a diagnostic.
    It returns False if a connection or query fails rather than propagating
    the database exception to the caller.
    """
    try:
        # Open a connection managed by the engine and execute a harmless query.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception:
        # Do not expose database credentials or internal connection details
        # through this boolean result. Detailed logging can be added separately.
        return False
