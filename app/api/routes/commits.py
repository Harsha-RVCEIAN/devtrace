"""
app/api/routes/commits.py

Purpose:
    FastAPI routes for Git commit ingestion and provenance queries.

Endpoints:
    POST /commits
        Ingest a Git commit and its changeset atomically.

    GET /commits/{commit_id}
        Retrieve one Git commit and its associated changed files.

    GET /projects/{project_id}/commits
        List all Git commits belonging to an accessible project.

Security:
    Project membership is required for all operations. Missing records and
    inaccessible records return 404 to avoid disclosing private project UUIDs.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import GitCommit, ProjectMember
from app.schemas.commit import CommitCreate, CommitResponse
from app.services.commit_service import (
    get_commit,
    ingest_commit_with_changes,
    list_project_commits,
)

router = APIRouter(tags=["Commits"])


def _require_project_membership(
    db: DatabaseSession,
    project_id: UUID,
    user_id: UUID,
) -> None:
    """Raise 404 unless the user belongs to the requested project."""
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )


@router.post(
    "/commits",
    response_model=CommitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a Git commit with its code changes",
)
def create_commit(
    payload: CommitCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CommitResponse:
    """
    Ingest a Git commit and its changeset atomically.

    Requires the current user to be a member of the target project.
    If a commit hash already exists in this project, HTTP 409 Conflict is returned.
    """
    # 1. Authorize project membership
    _require_project_membership(db, payload.project_id, current_user.user_id)

    # 2. Persist commit and code changes via the service layer
    try:
        commit = ingest_commit_with_changes(
            db=db,
            commit_data=payload,
            user_id=current_user.user_id,
        )
        return CommitResponse.model_validate(commit)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Commit already exists or violates a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record the Git commit.",
        ) from exc


@router.get(
    "/commits/{commit_id}",
    response_model=CommitResponse,
    summary="Get a Git commit and its changed files",
)
def get_one_commit(
    commit_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CommitResponse:
    """Retrieve a commit and its changes after verifying membership."""
    commit = get_commit(db, commit_id)
    if commit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commit not found.",
        )

    _require_project_membership(db, commit.project_id, current_user.user_id)
    return CommitResponse.model_validate(commit)


@router.get(
    "/projects/{project_id}/commits",
    response_model=list[CommitResponse],
    summary="List Git commits in a project",
)
def get_project_commits(
    project_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CommitResponse]:
    """List commits belonging to a project, newest first."""
    _require_project_membership(db, project_id, current_user.user_id)

    commits = list_project_commits(
        db=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return [CommitResponse.model_validate(c) for c in commits]