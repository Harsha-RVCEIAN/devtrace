
"""
API routes for decision alternatives.

Endpoints:
    POST  /decisions/{decision_id}/alternatives
        Create an alternative for a decision.

    GET   /decisions/{decision_id}/alternatives
        List alternatives belonging to a decision.

    GET   /alternatives/{alternative_id}
        Retrieve one alternative.

    PATCH /alternatives/{alternative_id}
        Update an alternative's description or selection status.

Security:
    Every operation checks project membership through the parent Decision.
    A valid alternative UUID alone is never sufficient to authorize access.

Transaction ownership:
    Database writes and transaction handling are delegated to the service
    layer. This module handles HTTP validation, authorization, and responses.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import Alternative, Decision, ProjectMember
from app.schemas.alternative import (
    AlternativeCreate,
    AlternativeResponse,
    AlternativeUpdate,
)
from app.services.alternative_service import (
    create_alternative,
    get_alternative,
    list_decision_alternatives,
    update_alternative,
)


router = APIRouter(tags=["Alternatives"])


def _require_decision_membership(
    db: DatabaseSession,
    decision_id: UUID,
    user_id: UUID,
) -> Decision:
    """
    Return the decision only if it belongs to a project the user can access.

    The Alternative ORM model does not contain project_id. Therefore,
    authorization must follow Alternative -> Decision -> ProjectMember.

    A 404 response is used for both missing decisions and inaccessible
    projects so the endpoint does not disclose another project's existence.
    """
    decision = db.scalar(
        select(Decision).where(Decision.decision_id == decision_id)
    )

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found.",
        )

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == decision.project_id,
            ProjectMember.user_id == user_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found.",
        )

    return decision


def _require_alternative_membership(
    db: DatabaseSession,
    alternative_id: UUID,
    user_id: UUID,
) -> Alternative:
    """
    Retrieve an alternative after verifying access through its parent decision.

    This helper prevents direct access to an alternative belonging to a
    different project's decision.
    """
    alternative = get_alternative(db, alternative_id)

    if alternative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alternative not found.",
        )

    _require_decision_membership(
        db=db,
        decision_id=alternative.decision_id,
        user_id=user_id,
    )

    return alternative


@router.post(
    "/decisions/{decision_id}/alternatives",
    response_model=AlternativeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a decision alternative",
)
def create_decision_alternative(
    decision_id: UUID,
    payload: AlternativeCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Alternative:
    """
    Create an alternative for an accessible decision.

    The decision must exist and belong to a project of which the current user
    is a member. Request validation is performed by AlternativeCreate.
    """
    _require_decision_membership(
        db=db,
        decision_id=decision_id,
        user_id=current_user.user_id,
    )

    try:
        return create_alternative(
            db=db,
            decision_id=decision_id,
            description=payload.description,
            selection_status=payload.selection_status,
        )
    except ValueError as exc:
        # The service reports invalid parent references as ValueError.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        # The database may reject a duplicate or invalid constrained value.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The alternative conflicts with a database constraint.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the alternative.",
        ) from exc


@router.get(
    "/decisions/{decision_id}/alternatives",
    response_model=list[AlternativeResponse],
    summary="List alternatives for a decision",
)
def get_decision_alternatives(
    decision_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[Alternative]:
    """
    Return alternatives for an accessible decision.

    An empty list is a valid response when the decision has no alternatives.
    """
    _require_decision_membership(
        db=db,
        decision_id=decision_id,
        user_id=current_user.user_id,
    )

    return list_decision_alternatives(
        db=db,
        decision_id=decision_id,
    )


@router.get(
    "/alternatives/{alternative_id}",
    response_model=AlternativeResponse,
    summary="Retrieve an alternative",
)
def get_one_alternative(
    alternative_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Alternative:
    """Retrieve an alternative only if the user can access its project."""
    return _require_alternative_membership(
        db=db,
        alternative_id=alternative_id,
        user_id=current_user.user_id,
    )


@router.patch(
    "/alternatives/{alternative_id}",
    response_model=AlternativeResponse,
    summary="Update an alternative",
)
def patch_alternative(
    alternative_id: UUID,
    payload: AlternativeUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Alternative:
    """
    Partially update an alternative after authorization.

    Only description and selection_status can be modified. The parent decision
    is immutable through this endpoint.
    """
    # model_fields_set distinguishes omitted fields from explicitly supplied
    # fields, allowing us to reject an empty PATCH request.
    if not payload.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one update field must be supplied.",
        )

    alternative = _require_alternative_membership(
        db=db,
        alternative_id=alternative_id,
        user_id=current_user.user_id,
    )

    try:
        return update_alternative(
            db=db,
            alternative=alternative,
            update_data=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The alternative update conflicts with a database constraint.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the alternative.",
        ) from exc
