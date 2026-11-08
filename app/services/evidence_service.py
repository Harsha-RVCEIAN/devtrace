
"""
Service layer for decision evidence.

Responsibilities:
    - Retrieve individual evidence records.
    - List evidence associated with a decision.
    - Create evidence records after validating the parent decision.
    - Handle transaction commits, refreshes, and rollbacks.

Architecture:
    API route -> Evidence service -> SQLAlchemy ORM -> PostgreSQL

Authorization:
    This service validates the existence of the parent decision. API routes
    must additionally verify that the authenticated user belongs to the
    project containing that decision.

The Evidence ORM model is the source of truth for database field names,
foreign keys, and database-generated defaults.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import Decision, Evidence


def get_evidence(
    db: Session,
    evidence_id: UUID,
) -> Evidence | None:
    """
    Retrieve one evidence record using its primary key.

    Args:
        db: Active SQLAlchemy database session.
        evidence_id: UUID of the evidence record.

    Returns:
        The Evidence ORM instance if it exists; otherwise None.

    Transaction behavior:
        This operation is read-only and does not commit.
    """
    statement = select(Evidence).where(
        Evidence.evidence_id == evidence_id
    )

    return db.scalar(statement)


def list_decision_evidence(
    db: Session,
    decision_id: UUID,
) -> list[Evidence]:
    """
    List all evidence records belonging to a decision.

    Args:
        db: Active SQLAlchemy database session.
        decision_id: UUID of the parent decision.

    Returns:
        A list of evidence records, ordered by capture timestamp and then
        evidence UUID. Decisions with no evidence return an empty list.

    Note:
        The caller must enforce project membership before exposing results.
    """
    statement = (
        select(Evidence)
        .where(Evidence.decision_id == decision_id)
        .order_by(
            Evidence.captured_at.asc(),
            Evidence.evidence_id.asc(),
        )
    )

    return list(db.scalars(statement).all())


def _ensure_decision_exists(
    db: Session,
    decision_id: UUID,
) -> Decision:
    """
    Confirm that the decision receiving the evidence exists.

    Args:
        db: Active SQLAlchemy database session.
        decision_id: UUID of the parent decision.

    Returns:
        The existing Decision ORM instance.

    Raises:
        ValueError: If the decision does not exist.
    """
    decision = db.scalar(
        select(Decision).where(Decision.decision_id == decision_id)
    )

    if decision is None:
        raise ValueError("Decision not found.")

    return decision


def create_evidence(
    db: Session,
    decision_id: UUID,
    evidence_type: str,
    source_reference: str,
) -> Evidence:
    """
    Create evidence supporting an existing engineering decision.

    Args:
        db: Active SQLAlchemy database session.
        decision_id: UUID of the decision being supported.
        evidence_type: Category of the supporting material, such as
            'research_paper', 'benchmark', or 'code_review'.
        source_reference: Locator for the source, such as a URL,
            document reference, commit hash, or issue identifier.

    Returns:
        The persisted Evidence ORM instance.

    Raises:
        ValueError: If the parent decision does not exist.
        SQLAlchemyError: If the database write fails.

    Transaction behavior:
        Commit and refresh on success; rollback on SQLAlchemy errors.

    Design decision:
        captured_at is intentionally omitted from the constructor because
        the existing ORM model supplies a server-side default timestamp.
        This keeps the timestamp generated consistently by PostgreSQL.
    """
    try:
        # Validate the parent decision before creating the child record.
        _ensure_decision_exists(db, decision_id)

        evidence = Evidence(
            decision_id=decision_id,
            evidence_type=evidence_type,
            source_reference=source_reference,
        )

        db.add(evidence)

        # Execute pending SQL and check database constraints.
        db.flush()

        # Persist the evidence record.
        db.commit()

        # Load the generated UUID and database-generated timestamp.
        db.refresh(evidence)

        return evidence

    except SQLAlchemyError:
        # Restore the session to a usable state after database failures.
        db.rollback()
        raise
