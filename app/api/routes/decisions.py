
"""
FastAPI routes for engineering decision management.

Endpoints:
    POST  /projects/{project_id}/decisions
    GET   /projects/{project_id}/decisions
    GET   /decisions/{decision_id}
    PATCH /decisions/{decision_id}

Authorization:
    A user must belong to the relevant project before accessing its decisions.
    A 404 response is used for missing membership or inaccessible records to
    avoid revealing whether another project's records exist.

Database writes and transaction handling are delegated to decision_service.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import Decision, ProjectMember
from app.schemas.decision import (
    DecisionCreate,
    DecisionResponse,
    DecisionUpdate,
)
from app.services.decision_service import (
    create_decision,
    get_decision,
    list_project_decisions,
    update_decision,
)

router = APIRouter(tags=["Decisions"])


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
    "/projects/{project_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an engineering decision",
)
def create_project_decision(
    project_id: UUID,
    decision_data: DecisionCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> DecisionResponse:
    """Create a decision after confirming project membership."""
    _require_project_membership(db, project_id, current_user.user_id)

    try:
        decision = create_decision(db, project_id, decision_data)
        return DecisionResponse.model_validate(decision)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The decision conflicts with a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The decision could not be saved.",
        ) from exc


@router.get(
    "/projects/{project_id}/decisions",
    response_model=list[DecisionResponse],
    summary="List decisions in a project",
)
def get_project_decisions(
    project_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[DecisionResponse]:
    """Return decisions only to members of the requested project."""
    _require_project_membership(db, project_id, current_user.user_id)

    decisions = list_project_decisions(db, project_id)
    return [
        DecisionResponse.model_validate(decision)
        for decision in decisions
    ]


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
    summary="Get an engineering decision",
)
def get_one_decision(
    decision_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> DecisionResponse:
    """Retrieve a decision only if the current user belongs to its project."""
    decision = get_decision(db, decision_id)

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found.",
        )

    _require_project_membership(
        db,
        decision.project_id,
        current_user.user_id,
    )

    return DecisionResponse.model_validate(decision)


@router.patch(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
    summary="Update an engineering decision",
)
def patch_decision(
    decision_id: UUID,
    update_data: DecisionUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> DecisionResponse:
    """
    Update decision fields after checking membership.

    An empty PATCH request is rejected. To clear nullable fields, explicitly
    provide null for fields such as reason_text or reason_confidence.
    """
    if not update_data.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be supplied.",
        )

    decision = get_decision(db, decision_id)

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found.",
        )

    _require_project_membership(
        db,
        decision.project_id,
        current_user.user_id,
    )

    try:
        updated = update_decision(db, decision, update_data)
        return DecisionResponse.model_validate(updated)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The decision conflicts with a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The decision could not be updated.",
        ) from exc
