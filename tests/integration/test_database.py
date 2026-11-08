
"""
Integration tests for DevTrace database connectivity and constraints.

These tests verify that PostgreSQL is reachable, the expected relational
tables exist, and the database rejects duplicate project memberships.
Each test uses the shared db_session fixture, which rolls back its
transaction so test data does not persist between tests.
"""

from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models.entities import Project, ProjectMember, User


def create_user(session):
    """Create and flush a uniquely named user for an integration test."""
    suffix = uuid4().hex[:12]
    user = User(
        name=f"Integration Test User {suffix}",
        email=f"{suffix}@example.test",
    )
    session.add(user)
    session.flush()
    return user


def create_project(session):
    """Create and flush a project for an integration test."""
    project = Project(
        project_name=f"Test Project {uuid4().hex[:8]}",
        description="Integration test project",
    )
    session.add(project)
    session.flush()
    return project


def test_database_connection(test_engine):
    """Verify that the test database accepts a basic SQL query."""
    with test_engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1


def test_expected_tables_exist(test_engine):
    """Verify that all required DevTrace relational tables exist."""
    tables = set(inspect(test_engine).get_table_names())

    expected = {
        "app_user",
        "project",
        "project_member",
        "ai_interaction",
        "decision",
        "alternative",
        "evidence",
        "git_commit",
        "code_change",
    }

    assert expected.issubset(tables)


def test_duplicate_project_membership_is_rejected(db_session):
    """
    Verify that PostgreSQL enforces the composite membership primary key.

    A nested transaction isolates the expected constraint violation.
    Expunging the first membership before adding the duplicate prevents
    SQLAlchemy's identity map from warning about two objects with the
    same identity. The database remains responsible for rejecting it.
    """
    user = create_user(db_session)
    project = create_project(db_session)

    membership = ProjectMember(
        project_id=project.project_id,
        user_id=user.user_id,
        role="member",
    )
    db_session.add(membership)
    db_session.flush()

    # Keep the first row in the database, but remove its ORM object from
    # the session identity map before constructing the duplicate object.
    db_session.expunge(membership)

    duplicate = ProjectMember(
        project_id=project.project_id,
        user_id=user.user_id,
        role="member",
    )

    # The savepoint allows the expected failed insert to be rolled back
    # without invalidating the outer test transaction.
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(duplicate)
            db_session.flush()
