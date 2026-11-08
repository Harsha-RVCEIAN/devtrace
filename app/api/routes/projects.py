
"""
DevTrace Project API Routes
===========================

Purpose
-------
Exposes HTTP endpoints for creating, listing, retrieving, and updating
projects. Request and response payloads are validated using Pydantic
schemas, while business operations are delegated to project_service.

Architectural Responsibility
----------------------------
The route layer translates HTTP requests into service calls and translates
expected failures into HTTP responses. It should not duplicate repository
queries or take over business transaction management.

Project Access Control
----------------------
Project retrieval and updates require the requesting user to be a member
of the specified project. The listing endpoint filters projects by the
current user's membership rather than returning every project in the
database.

For a missing project and a project that the user is not allowed to view,
the route returns the same 404 response to avoid revealing whether a
private project exists.

Project Creation
----------------
The service creates the project and its initial owner membership as one
transaction. The route maps database failures to HTTP errors and ensures
the session is rolled back if an error escapes the service operation.

Security Limitation
-------------------
The current CurrentUser dependency uses a development-only X-User-ID
header. It does not securely authenticate the caller. Replace that
mechanism before exposing the API to untrusted clients.

Dependencies
------------
- app.api.dependencies: current-user and database-session dependencies.
- app.schemas.project: validated project request/response models.
- app.services.project_service: project business logic and transactions.
- app.models.entities: project and membership entities used for access checks.

Current update policy:
Any project member may update project metadata. If the project requires
owner-only updates, that policy must be enforced explicitly before calling
the update service.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.models.entities import Project, ProjectMember, User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])

# Use the same request-scoped session mechanism as the rest of the API.
DatabaseSession = Annotated[Session, Depends(get_db)]


def _require_project_membership(
    db: Session,
    project_id: UUID,
    user_id: UUID,
) -> Project:
    """
    Find a project only when the specified user is a project member.

    This helper combines project lookup and membership verification in a
    single query. It prevents endpoints from returning a project merely
    because the caller knows its UUID.

    Args:
        db: Request-scoped SQLAlchemy session.
        project_id: UUID of the requested project.
        user_id: UUID of the user whose membership must be verified.

    Returns:
        The Project entity when the user belongs to the project.

    Raises:
        HTTPException: HTTP 404 if the project does not exist or the user
            is not a member. Using the same response avoids disclosing
            another user's private project existence.
    """
    statement = (
        select(Project)
        .join(
            ProjectMember,
            ProjectMember.project_id == Project.project_id,
        )
        .where(
            Project.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )

    project = db.scalar(statement)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return project


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    project_data: ProjectCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Project:
    """
    Create a project owned by the currently resolved user.

    The ProjectCreate schema validates incoming project metadata. The
    service creates both the Project row and the creator's ProjectMember
    row, assigning the creator the owner role.

    Args:
        project_data: Validated project name, description, and repository URL.
        db: Request-scoped database session.
        current_user: Existing user resolved by the identity dependency.

    Returns:
        The newly created Project entity, serialized using ProjectResponse.

    Raises:
        HTTPException: HTTP 409 for a database integrity conflict and HTTP
            500 for an unexpected database operation failure.
    """
    try:
        return project_service.create_project(
            db=db,
            project_data=project_data,
            creator_id=current_user.user_id,
        )

    except IntegrityError as exc:
        # A failed transaction must be rolled back before the session can
        # safely be reused or closed.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project could not be created because of a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating the project.",
        ) from exc


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: DatabaseSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Project]:
    """
    List projects of which the current user is a member.

    Pagination limits the number of rows returned in one request. The
    membership join ensures that unrelated projects are not exposed.

    Args:
        db: Request-scoped SQLAlchemy session.
        current_user: Existing user resolved by the identity dependency.
        limit: Maximum number of results, from 1 through 100.
        offset: Number of results to skip, zero or greater.

    Returns:
        A list of project entities visible to the current user.
    """
    statement = (
        select(Project)
        .join(
            ProjectMember,
            ProjectMember.project_id == Project.project_id,
        )
        .where(ProjectMember.user_id == current_user.user_id)
        .order_by(Project.created_at.desc(), Project.project_id)
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(statement).all())


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Project:
    """
    Retrieve one project after checking membership.

    Args:
        project_id: UUID path parameter identifying the project.
        db: Request-scoped SQLAlchemy session.
        current_user: Existing user resolved by the identity dependency.

    Returns:
        The requested Project entity.

    Raises:
        HTTPException: HTTP 404 if the project is missing or the requester
            is not a member.
    """
    return _require_project_membership(
        db,
        project_id,
        current_user.user_id,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Project:
    """
    Update project metadata after verifying project membership.

    The schema rejects invalid update payloads before the service is called.
    The current policy permits any project member to edit metadata. If
    updates must be owner-only, verify ProjectMember.role == "owner" here
    before proceeding.

    Args:
        project_id: UUID path parameter identifying the project.
        project_data: Validated fields to update.
        db: Request-scoped SQLAlchemy session.
        current_user: Existing user resolved by the identity dependency.

    Returns:
        The updated Project entity.

    Raises:
        HTTPException: HTTP 404 when the project is missing or inaccessible,
            HTTP 409 for integrity conflicts, or HTTP 500 for database errors.
    """
    # Check access before passing the project ID to the update service.
    _require_project_membership(db, project_id, current_user.user_id)

    try:
        project = project_service.update_project(
            db=db,
            project_id=project_id,
            project_data=project_data,
        )

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project update conflicts with a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating the project.",
        ) from exc

    # Recheck the result in case the project disappeared between the access
    # query and the service query.
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return project
