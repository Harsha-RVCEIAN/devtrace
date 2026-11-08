
"""
API routes for decision evidence.

Endpoints:
    POST /decisions/{decision_id}/evidence
        Attach evidence to a decision.

    GET /decisions/{decision_id}/evidence
        List evidence associated with a decision.

    GET /evidence/{evidence_id}
        Retrieve an individual evidence record.

Security:
    Evidence records do not have a project_id column. Access is therefore
    checked through the parent Decision and its associated project membership.

Transaction ownership:
    The evidence service owns database writes and transaction management.
    This router handles request validation, authorization, and HTTP errors.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import Decision, Evidence, ProjectMember
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.evidence_service import (
    create_evidence,
    get_evidence,
    list_decision_evidence,
)


router = APIRouter(tags=["Evidence"])


def _require_decision_membership(
    db: DatabaseSession,
    decision_id: UUID,
    user_id: UUID,
) -> Decision:
    """
    Verify that the decision exists and belongs to an accessible project.

    Both a missing decision and a decision in another user's project return
    404. This avoids disclosing the existence of inaccessible records.
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


def _require_evidence_membership(
    db: DatabaseSession,
    evidence_id: UUID,
    user_id: UUID,
) -> Evidence:
    """
    Retrieve evidence only after verifying membership in its decision's project.

    The parent decision provides the project context required for authorization.
    """
    evidence = get_evidence(db, evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    _require_decision_membership(
        db=db,
        decision_id=evidence.decision_id,
        user_id=user_id,
    )

    return evidence


@router.post(
    "/decisions/{decision_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add evidence to a decision",
)
def add_decision_evidence(
    decision_id: UUID,
    payload: EvidenceCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Evidence:
    """
    Attach supporting evidence to an accessible decision.

    The evidence type and source reference are validated by EvidenceCreate.
    The database generates the evidence UUID and capture timestamp.
    """
    _require_decision_membership(
        db=db,
        decision_id=decision_id,
        user_id=current_user.user_id,
    )

    try:
        return create_evidence(
            db=db,
            decision_id=decision_id,
            evidence_type=payload.evidence_type,
            source_reference=payload.source_reference,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The evidence conflicts with a database constraint.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create evidence.",
        ) from exc


@router.get(
    "/decisions/{decision_id}/evidence",
    response_model=list[EvidenceResponse],
    summary="List evidence for a decision",
)
def get_decision_evidence(
    decision_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[Evidence]:
    """
    Return evidence for a decision the current user can access.

    Returns an empty list when no evidence has been recorded.
    """
    _require_decision_membership(
        db=db,
        decision_id=decision_id,
        user_id=current_user.user_id,
    )

    return list_decision_evidence(
        db=db,
        decision_id=decision_id,
    )


@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Retrieve an evidence record",
)
def get_one_evidence(
    evidence_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Evidence:
    """Retrieve an evidence record only when project membership is verified."""
    return _require_evidence_membership(
        db=db,
        evidence_id=evidence_id,
        user_id=current_user.user_id,
    )
