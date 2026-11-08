
"""
DevTrace Project Repository
===========================

Purpose
-------
Implements database-access operations for Project entities using the
existing SQLAlchemy model and relational database schema.

Architectural Responsibility
----------------------------
This module provides the persistence interface used by project services.
It supports project creation, retrieval by UUID, paginated listing, and
allowlisted metadata updates. Keeping these operations in one module
prevents database-query logic from being duplicated across API endpoints.

Transaction Management
----------------------
The repository receives an existing SQLAlchemy Session from its caller.
It does not create a new session and does not commit or roll back the
transaction. flush() is used when SQL must be sent to the database before
the surrounding transaction is committed.

This is important when an operation spans multiple tables. For example,
project creation must persist the Project row before creating its initial
ProjectMember row, while keeping both changes inside the same transaction.

Data Integrity and Security
---------------------------
Queries are constructed with SQLAlchemy expressions rather than by
concatenating untrusted values into SQL strings. Update operations use an
explicit allowlist so callers cannot modify arbitrary ORM attributes
through this repository function.

The repository does not enforce project membership or user authorization.
Callers in the service/API layers must enforce those policies before
returning protected project data or modifying a project.

Dependencies
------------
- app.models.entities.Project: the existing project ORM entity.
- sqlalchemy.orm.Session: caller-managed database session.
- sqlalchemy.select: SQLAlchemy query construction.

This module does not implement HTTP status codes, Pydantic request
validation, authentication, authorization, or transaction ownership.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Project


def create_project(
    db: Session,
    *,
    project_name: str,
    description: str | None = None,
    repository_url: str | None = None,
) -> Project:
    """
    Stage a new project in the current database transaction.

    A Project entity is created using the supplied values and added to the
    caller's SQLAlchemy session. flush() sends pending SQL to the database
    without committing the transaction, allowing the generated project ID
    to be used when creating related records.

    Args:
        db: Active SQLAlchemy session supplied by the service layer.
        project_name: Non-empty project name validated by the request schema.
        description: Optional description of the project.
        repository_url: Optional URL of the project's source repository.

    Returns:
        The new Project ORM entity, including its generated project ID.

    Raises:
        SQLAlchemyError: If the database rejects the insert or a constraint
            is violated. The caller must roll back the failed transaction.

    Transaction Behaviour:
        The function deliberately does not commit. The service layer may
        need to create related records before committing the operation.
    """
    project = Project(
        project_name=project_name,
        description=description,
        repository_url=repository_url,
    )

    # Add the entity to the existing unit of work rather than creating a
    # separate session that could not share the caller's transaction.
    db.add(project)

    # Flush obtains database-generated values without making the transaction
    # permanent. The service can now use project.project_id for membership.
    db.flush()

    return project


def get_project_by_id(
    db: Session,
    project_id: UUID,
) -> Project | None:
    """
    Retrieve a project using its UUID primary key.

    Args:
        db: Active SQLAlchemy session.
        project_id: UUID identifying the project.

    Returns:
        The matching Project entity, or None if the project does not exist.

    Security Note:
        This function checks only whether a project exists. It does not
        establish that the requesting user is authorized to access it.
    """
    statement = select(Project).where(Project.project_id == project_id)

    return db.scalar(statement)


def list_projects(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Project]:
    """
    Retrieve a bounded page of project records.

    Results are sorted by creation time, newest first. The project UUID
    provides a secondary sort key so records with identical timestamps
    have a deterministic ordering.

    Args:
        db: Active SQLAlchemy session.
        limit: Maximum number of rows to return, from 1 through 100.
        offset: Number of rows to skip; must be zero or greater.

    Returns:
        A list of Project entities. An empty list means no rows matched.

    Raises:
        ValueError: If limit or offset is outside the permitted range.

    Security Note:
        This is a general persistence query. API endpoints must apply
        membership filters when listing projects for a particular user.
    """
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")

    if offset < 0:
        raise ValueError("offset must be zero or greater.")

    statement = (
        select(Project)
        .order_by(Project.created_at.desc(), Project.project_id)
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(statement).all())


def update_project(
    db: Session,
    project: Project,
    *,
    updates: dict[str, object],
) -> Project:
    """
    Apply supported metadata changes to an existing Project entity.

    Only explicitly allowed fields may be modified. Request schemas should
    validate API values before this function is called, while this repository
    independently rejects unexpected field names.

    Args:
        db: Active SQLAlchemy session.
        project: Existing Project ORM entity to modify.
        updates: Mapping containing fields to update and their new values.

    Returns:
        The modified Project entity after the changes have been flushed.

    Raises:
        ValueError: If an unsupported field is supplied or the project name
            is empty or contains only whitespace.
        SQLAlchemyError: If the database rejects the update.

    Transaction Behaviour:
        The function flushes but does not commit. Its caller owns the
        transaction and decides whether to commit or roll back.
    """
    allowed_fields = {
        "project_name",
        "description",
        "repository_url",
    }

    # Reject unknown keys instead of silently changing arbitrary model
    # attributes. This also protects against incorrect internal callers.
    unexpected_fields = set(updates) - allowed_fields

    if unexpected_fields:
        raise ValueError(
            "Unsupported project update fields: "
            + ", ".join(sorted(unexpected_fields))
        )

    for field_name, value in updates.items():
        if field_name == "project_name":
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Project name must not be empty.")

            # Normalize whitespace even if the caller bypasses the API schema.
            value = value.strip()

        setattr(project, field_name, value)

    # Send changes to the database while preserving the caller's control
    # over the final commit or rollback.
    db.flush()

    return project
