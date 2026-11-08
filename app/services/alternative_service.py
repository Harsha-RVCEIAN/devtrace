
"""
Service layer for decision alternatives.

Responsibilities:
    - Retrieve alternatives belonging to a decision.
    - Create alternatives with validated parent-decision references.
    - Update an existing alternative without allowing its parent decision
      to be changed through the update operation.
    - Manage transaction commits, refreshes, and rollbacks.

Architecture:
    API route -> Alternative service -> SQLAlchemy ORM -> PostgreSQL

Authorization is intentionally handled by the API layer. Routes must verify
that the current user is a member of the project associated with the parent
decision before returning or modifying alternatives.

The Alternative ORM model and its database constraints remain the source
of truth for persisted data.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import Alternative, Decision


def get_alternative(
    db: Session,
    alternative_id: UUID,
) -> Alternative | None:
    """
    Retrieve one alternative by its primary key.

    Args:
        db: Active SQLAlchemy database session.
        alternative_id: UUID of the alternative to retrieve.

    Returns:
        The Alternative ORM instance if found; otherwise None.

    Transaction behavior:
        This function performs a read-only query and does not commit.
    """
    statement = select(Alternative).where(
        Alternative.alternative_id == alternative_id
    )

    return db.scalar(statement)


def list_decision_alternatives(
    db: Session,
    decision_id: UUID,
) -> list[Alternative]:
    """
    Retrieve all alternatives associated with one decision.

    Results are ordered by alternative UUID to provide deterministic
    ordering. If chronological ordering is required in the future, the
    ORM model will need an appropriate creation timestamp.

    Args:
        db: Active SQLAlchemy database session.
        decision_id: UUID of the parent decision.

    Returns:
        A list of Alternative ORM instances. An empty list is returned
        when the decision has no alternatives.

    Note:
        The caller must verify access to the parent decision's project.
    """
    statement = (
        select(Alternative)
        .where(Alternative.decision_id == decision_id)
        .order_by(Alternative.alternative_id.asc())
    )

    return list(db.scalars(statement).all())


def _ensure_decision_exists(
    db: Session,
    decision_id: UUID,
) -> Decision:
    """
    Validate the parent decision before creating an alternative.

    Checking the parent explicitly gives the service a clear error instead
    of relying exclusively on a database foreign-key violation.

    Args:
        db: Active SQLAlchemy database session.
        decision_id: UUID of the required parent decision.

    Returns:
        The existing Decision ORM instance.

    Raises:
        ValueError: If no decision with the supplied ID exists.
    """
    decision = db.scalar(
        select(Decision).where(Decision.decision_id == decision_id)
    )

    if decision is None:
        raise ValueError("Decision not found.")

    return decision


def create_alternative(
    db: Session,
    decision_id: UUID,
    description: str,
    selection_status: str = "considered",
) -> Alternative:
    """
    Create and persist an alternative for an existing decision.

    Args:
        db: Active SQLAlchemy database session.
        decision_id: UUID of the decision that owns this alternative.
        description: Explanation of the alternative.
        selection_status: One of the database-supported statuses:
            'selected', 'rejected', or 'considered'.

    Returns:
        The persisted Alternative ORM instance.

    Raises:
        ValueError: If the parent decision does not exist.
        SQLAlchemyError: If persistence fails.

    Transaction behavior:
        This function owns its write transaction. It commits on success,
        refreshes the ORM instance so database-generated values are current,
        and rolls back if a database operation fails.

    Design decision:
        The decision_id is supplied separately rather than accepted from
        arbitrary request-body data. This prevents a client from silently
        changing the parent relationship during creation.
    """
    try:
        # Validate the parent before creating the child record.
        _ensure_decision_exists(db, decision_id)

        alternative = Alternative(
            decision_id=decision_id,
            description=description,
            selection_status=selection_status,
        )

        db.add(alternative)

        # Flush sends pending SQL to PostgreSQL and detects constraint
        # violations before the transaction is committed.
        db.flush()

        # Commit makes the alternative durable.
        db.commit()

        # Refresh retrieves database-generated values, including the UUID.
        db.refresh(alternative)

        return alternative

    except SQLAlchemyError:
        # Never leave a failed transaction open for the next request.
        db.rollback()
        raise


def update_alternative(
    db: Session,
    alternative: Alternative,
    update_data: dict,
) -> Alternative:
    """
    Update the permitted fields of an existing alternative.

    Args:
        db: Active SQLAlchemy database session.
        alternative: Existing ORM instance retrieved by the caller.
        update_data: Validated fields supplied by the API layer.

    Returns:
        The updated Alternative ORM instance.

    Raises:
        ValueError: If no permitted update fields are supplied.
        SQLAlchemyError: If the update cannot be persisted.

    Transaction behavior:
        The service commits the update and refreshes the instance on success.
        On SQLAlchemy errors, the transaction is rolled back.

    Security and integrity:
        Only description and selection_status are accepted. The decision_id
        and alternative_id are deliberately excluded from the update
        allowlist so the record cannot be reassigned to another decision.
    """
    allowed_fields = {"description", "selection_status"}

    # Filter the payload instead of blindly applying arbitrary client fields.
    changes = {
        key: value
        for key, value in update_data.items()
        if key in allowed_fields
    }

    if not changes:
        raise ValueError("No permitted alternative fields were supplied.")

    try:
        for field, value in changes.items():
            setattr(alternative, field, value)

        db.flush()
        db.commit()
        db.refresh(alternative)

        return alternative

    except SQLAlchemyError:
        db.rollback()
        raise
