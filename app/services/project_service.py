
"""
DevTrace project service.

This module implements the business logic for creating, retrieving, listing,
and updating projects. It coordinates database repositories and manages
transaction boundaries when an operation involves multiple database records.

Project creation must be atomic: the project and its creator's membership
are persisted together, or both operations are rolled back. The service does
not define HTTP routes or expose database credentials.
"""

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import Project, ProjectMember
from app.repositories import project_repository
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(
    db: Session,
    project_data: ProjectCreate,
    creator_id: UUID,
) -> Project:
    """
    Create a project and register its creator as the initial member.

    The caller supplies an authenticated creator's ID. The creator must
    already exist in app_user; the database foreign key enforces this.

    The function commits only after both records have been flushed
    successfully. Any database failure rolls back the whole transaction.
    """
    try:
        project = project_repository.create_project(
            db,
            project_name=project_data.project_name,
            description=project_data.description,
            repository_url=(
                str(project_data.repository_url)
                if project_data.repository_url is not None
                else None
            ),
        )

        # Flush the project first so its generated project_id is available.
        db.flush()

        # Every project starts with its creator as a member.
        creator_membership = ProjectMember(
            project_id=project.project_id,
            user_id=creator_id,
            role="owner",
        )
        db.add(creator_membership)
        db.flush()

        # Commit only after the project and membership both succeed.
        db.commit()
        db.refresh(project)

        return project

    except SQLAlchemyError:
        db.rollback()
        raise


def get_project(db: Session, project_id: UUID) -> Project | None:
    """Return a project by its ID, or None when it does not exist."""
    return project_repository.get_project_by_id(db, project_id)


def list_projects(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Project]:
    """Return a paginated list of projects."""
    return project_repository.list_projects(
        db,
        limit=limit,
        offset=offset,
    )


def update_project(
    db: Session,
    project_id: UUID,
    project_data: ProjectUpdate,
) -> Project | None:
    """
    Update an existing project.

    Returns None if the project does not exist. Only fields accepted by
    ProjectUpdate are passed to the repository.
    """
    project = project_repository.get_project_by_id(db, project_id)

    if project is None:
        return None

    updates = project_data.model_dump(exclude_unset=True)

    # Convert Pydantic's HttpUrl value to a plain string for the DB column.
    if updates.get("repository_url") is not None:
        updates["repository_url"] = str(updates["repository_url"])

    try:
        updated_project = project_repository.update_project(
            db,
            project,
            updates=updates,
        )
        db.commit()
        db.refresh(updated_project)
        return updated_project

    except SQLAlchemyError:
        db.rollback()
        raise
