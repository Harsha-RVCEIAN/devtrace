
"""
Service-layer operations for engineering decisions.

Responsibilities:
    - Create and retrieve decisions.
    - List decisions belonging to a project.
    - Apply validated updates to existing decisions.
    - Verify that linked interactions and replacement decisions belong to
      the same project.
    - Commit successful writes and roll back failed database transactions.

Authorization is performed by the API routes before service calls. Database
constraints remain the final safeguard for referential integrity.

Transaction policy:
    Each write operation commits on success. SQLAlchemy errors trigger a
    rollback and are propagated to the API layer. The request-scoped session
    is not closed here.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import AIInteraction, Decision
from app.schemas.decision import DecisionCreate, DecisionUpdate


def get_decision(
    db: Session,
    decision_id: UUID,
) -> Decision | None:
    """Return one decision by primary key, or None if it does not exist."""
    return db.get(Decision, decision_id)


def list_project_decisions(
    db: Session,
    project_id: UUID,
) -> list[Decision]:
    """Return decisions for one project, newest decisions first where possible."""
    statement = (
        select(Decision)
        .where(Decision.project_id == project_id)
        .order_by(Decision.decision_id.desc())
    )
    return list(db.scalars(statement).all())


def _validate_project_links(
    db: Session,
    project_id: UUID,
    interaction_id: UUID | None,
    replaced_by_decision_id: UUID | None,
    current_decision_id: UUID | None = None,
) -> None:
    """
    Validate optional references before writing a decision.

    A linked AI interaction must belong to the same project. A replacement
    decision must also belong to the same project and cannot reference the
    decision currently being updated.
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
                "The specified AI interaction does not exist in this project."
            )

    if replaced_by_decision_id is not None:
        if replaced_by_decision_id == current_decision_id:
            raise ValueError("A decision cannot replace itself.")

        replacement = db.scalar(
            select(Decision).where(
                Decision.decision_id == replaced_by_decision_id,
                Decision.project_id == project_id,
            )
        )
        if replacement is None:
            raise ValueError(
                "The replacement decision does not exist in this project."
            )


def create_decision(
    db: Session,
    project_id: UUID,
    decision_data: DecisionCreate,
) -> Decision:
    """
    Create and persist a decision inside an existing project.

    Args:
        db: Active request-scoped SQLAlchemy session.
        project_id: Project authorized by the API route.
        decision_data: Validated decision request.

    Returns:
        The persisted and refreshed Decision instance.

    Raises:
        ValueError: If a referenced interaction is not in the project.
        SQLAlchemyError: If persistence fails; the transaction is rolled back.
    """
    _validate_project_links(
        db=db,
        project_id=project_id,
        interaction_id=decision_data.interaction_id,
        replaced_by_decision_id=None,
    )

    decision = Decision(
        project_id=project_id,
        interaction_id=decision_data.interaction_id,
        title=decision_data.title,
        description=decision_data.description,
        decision_type=decision_data.decision_type,
        status=decision_data.status,
        reason_text=decision_data.reason_text,
        reason_source_type=decision_data.reason_source_type,
        reason_confidence=decision_data.reason_confidence,
        decided_at=decision_data.decided_at,
    )

    try:
        db.add(decision)
        db.flush()
        db.commit()
        db.refresh(decision)
        return decision
    except SQLAlchemyError:
        db.rollback()
        raise


def update_decision(
    db: Session,
    decision: Decision,
    update_data: DecisionUpdate,
) -> Decision:
    """
    Apply supplied fields to an existing decision and persist the update.

    The decision must already have been retrieved through a project-scoped
    route so the caller can enforce membership before invoking this method.
    Fields not supplied by the client remain unchanged.
    """
    changes = update_data.model_dump(exclude_unset=True)

    # Validate links against the decision's existing project before mutation.
    interaction_id = changes.get("interaction_id", decision.interaction_id)
    replacement_id = changes.get(
        "replaced_by_decision_id",
        decision.replaced_by_decision_id,
    )

    _validate_project_links(
        db=db,
        project_id=decision.project_id,
        interaction_id=interaction_id,
        replaced_by_decision_id=replacement_id,
        current_decision_id=decision.decision_id,
    )

    try:
        # Use an explicit field allowlist rather than setattr on arbitrary
        # client-supplied keys. This prevents changing IDs or project ownership.
        allowed_fields = {
            "title",
            "description",
            "decision_type",
            "status",
            "reason_text",
            "reason_source_type",
            "reason_confidence",
            "interaction_id",
            "replaced_by_decision_id",
            "decided_at",
        }

        for field, value in changes.items():
            if field in allowed_fields:
                setattr(decision, field, value)

        db.add(decision)
        db.flush()
        db.commit()
        db.refresh(decision)
        return decision
    except SQLAlchemyError:
        db.rollback()
        raise
