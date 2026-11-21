"""
app/services/commit_service.py

Purpose:
    Service-layer operations for Git commits and associated code changes.

Responsibilities:
    - Ingest a Git commit along with its batch of changed files atomically.
    - Verify that any referenced AI interactions or decisions belong to the same project.
    - Enforce database transaction boundaries (commit on success, rollback on error).
    - Retrieve commits and changes for project provenance queries.

Architecture:
    API Route (HTTP validation) -> Commit Service (Transactions & Invariants) -> PostgreSQL
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import AIInteraction, CodeChange, Decision, GitCommit
from app.schemas.commit import CommitCreate


def _validate_provenance_references(
    db: Session,
    project_id: UUID,
    interaction_id: UUID | None,
    decision_id: UUID | None,
) -> None:
    """
    Ensure optional interaction and decision links belong to the same project.

    Prevents attaching a code change in Project A to an AI interaction or
    engineering decision from Project B.
    """
    if interaction_id is not None:
        interaction = db.scalar(
            select(AIInteraction).where(
                AIInteraction.interaction_id == interaction_id,
                AIInteraction.project_id == project_id,
            )
        )
        if interaction is None:
            raise ValueError(
                "Referenced AI interaction does not exist in this project."
            )

    if decision_id is not None:
        decision = db.scalar(
            select(Decision).where(
                Decision.decision_id == decision_id,
                Decision.project_id == project_id,
            )
        )
        if decision is None:
            raise ValueError(
                "Referenced decision does not exist in this project."
            )


def ingest_commit_with_changes(
    db: Session,
    commit_data: CommitCreate,
    user_id: UUID,
) -> GitCommit:
    """
    Persist a Git commit and all of its associated code changes atomically.

    Args:
        db: Active SQLAlchemy database session.
        commit_data: Validated commit and nested changes payload.
        user_id: Authenticated user ID (author of the commit in this project).

    Returns:
        GitCommit: The persisted commit object with `.changes` populated.

    Raises:
        ValueError: If a referenced interaction or decision is outside the project.
        SQLAlchemyError: If a database constraint fails. Triggers a complete rollback.
    """
    try:
        # 1. Create and stage the GitCommit entity
        commit = GitCommit(
            project_id=commit_data.project_id,
            user_id=user_id,
            commit_hash=commit_data.commit_hash,
            message=commit_data.message,
            commit_time=commit_data.commit_time,
        )
        db.add(commit)

        # Flush sends the INSERT statement so PostgreSQL generates commit.commit_id
        db.flush()

        # 2. Process each code change in the commit changeset
        created_changes: list[CodeChange] = []
        for change_item in commit_data.changes:
            # Validate optional provenance links against the project
            _validate_provenance_references(
                db=db,
                project_id=commit_data.project_id,
                interaction_id=change_item.interaction_id,
                decision_id=change_item.decision_id,
            )

            change = CodeChange(
                project_id=commit_data.project_id,
                commit_id=commit.commit_id,
                interaction_id=change_item.interaction_id,
                decision_id=change_item.decision_id,
                file_path=change_item.file_path,
                change_type=change_item.change_type,
                origin=change_item.origin,
                confidence=change_item.confidence,
                lines_added=change_item.lines_added,
                lines_deleted=change_item.lines_deleted,
                line_start=change_item.line_start,
                line_end=change_item.line_end,
            )
            db.add(change)
            created_changes.append(change)

        # Flush all code changes to check constraints (e.g., origin checks, line counts)
        db.flush()

        # Commit only after the commit and ALL code changes have succeeded
        db.commit()

        # Refresh commit to load server-generated defaults
        db.refresh(commit)

        # Attach changes to the commit instance for response serialization
        commit.changes = created_changes
        return commit

    except SQLAlchemyError:
        # Atomicity guarantee: discard all staged rows if anything fails
        db.rollback()
        raise


def get_commit(db: Session, commit_id: UUID) -> GitCommit | None:
    """Retrieve one commit by UUID, along with its attached code changes."""
    commit = db.get(GitCommit, commit_id)
    if commit is not None:
        statement = (
            select(CodeChange)
            .where(CodeChange.commit_id == commit_id)
            .order_by(CodeChange.file_path.asc())
        )
        commit.changes = list(db.scalars(statement).all())
    return commit


def list_project_commits(
    db: Session,
    project_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[GitCommit]:
    """Return commits belonging to a project, newest first."""
    statement = (
        select(GitCommit)
        .where(GitCommit.project_id == project_id)
        .order_by(GitCommit.commit_time.desc())
        .limit(limit)
        .offset(offset)
    )
    commits = list(db.scalars(statement).all())
    for c in commits:
        statement_changes = (
            select(CodeChange)
            .where(CodeChange.commit_id == c.commit_id)
            .order_by(CodeChange.file_path.asc())
        )
        c.changes = list(db.scalars(statement_changes).all())
    return commits