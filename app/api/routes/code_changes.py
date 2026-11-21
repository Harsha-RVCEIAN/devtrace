"""
app/api/routes/code_changes.py

Purpose:
    FastAPI routes for code change provenance inspection and updates.

Endpoints:
    GET /changes/{change_id}/provenance
        Retrieve the full provenance graph for a code change.

    PATCH /changes/{change_id}
        Update provenance links on an existing code change.

    GET /projects/{project_id}/code-changes
        List code changes in a project, optionally filtered to unattributed changes.

Security:
    Project membership is required for all operations. Missing records and
    inaccessible records return 404 to prevent UUID enumeration.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import ProjectMember
from app.schemas.code_change import (
    CodeChangeProvenanceResponse,
    CodeChangeUpdate,
)
from app.services.provenance_service import (
    get_code_change,
    get_code_change_provenance,
    list_project_code_changes,
    update_code_change_provenance,
)

router = APIRouter(tags=["Code Changes & Provenance"])


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


@router.get(
    "/changes/{change_id}/provenance",
    response_model=CodeChangeProvenanceResponse,
    summary="Get full provenance graph of a code change",
)
def get_change_provenance(
    change_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CodeChangeProvenanceResponse:
    """
    Trace a code change to its associated commit, AI interaction, and decision.

    Missing relationships remain explicitly null without inventing rationale.
    """
    change = get_code_change(db, change_id)
    if change is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code change not found.",
        )

    _require_project_membership(db, change.project_id, current_user.user_id)

    provenance = get_code_change_provenance(db, change_id)
    if provenance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code change not found.",
        )

    return provenance


@router.patch(
    "/changes/{change_id}",
    response_model=CodeChangeProvenanceResponse,
    summary="Update code change provenance links",
)
def patch_code_change(
    change_id: UUID,
    payload: CodeChangeUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CodeChangeProvenanceResponse:
    """
    Update provenance links on an existing code change.

    Can be used to attach an AI interaction or engineering decision
    to an unlinked code change.
    """
    if not payload.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be supplied.",
        )

    change = get_code_change(db, change_id)
    if change is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code change not found.",
        )

    _require_project_membership(db, change.project_id, current_user.user_id)

    try:
        update_code_change_provenance(db, change, payload)
        return get_code_change_provenance(db, change_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provenance update conflicts with a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update code change provenance.",
        ) from exc


@router.get(
    "/projects/{project_id}/code-changes",
    response_model=list[CodeChangeProvenanceResponse],
    summary="List code changes for a project",
)
def get_project_code_changes(
    project_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
    missing_provenance_only: Annotated[
        bool,
        Query(description="Filter to changes missing interaction or decision links"),
    ] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CodeChangeProvenanceResponse]:
    """
    List code changes in a project, optionally filtered to unattributed changes.

    When missing_provenance_only=true, queries changes missing interaction or decision links.
    """
    _require_project_membership(db, project_id, current_user.user_id)

    changes = list_project_code_changes(
        db=db,
        project_id=project_id,
        missing_provenance_only=missing_provenance_only,
        limit=limit,
        offset=offset,
    )

    results = []
    for c in changes:
        prov = get_code_change_provenance(db, c.change_id)
        if prov is not None:
            results.append(prov)
    return results