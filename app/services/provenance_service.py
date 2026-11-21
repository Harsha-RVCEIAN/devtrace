"""
app/services/provenance_service.py

Purpose:
    Service-layer operations for code change provenance tracing and updates.

Responsibilities:
    - Trace a code change to its linked commit, AI interaction, and decision graph.
    - Preserve explicit None for missing provenance links without guessing.
    - Update code change provenance while enforcing same-project isolation.
    - Query unattributed code changes using the PostgreSQL partial index.
"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import (
    AIInteraction,
    Alternative,
    CodeChange,
    Decision,
    Evidence,
    GitCommit,
)
from app.schemas.code_change import (
    AlternativeSummary,
    CodeChangeProvenanceResponse,
    CodeChangeUpdate,
    CommitSummary,
    DecisionSummary,
    EvidenceSummary,
    InteractionSummary,
)


def get_code_change(db: Session, change_id: UUID) -> CodeChange | None:
    """Retrieve one code change entity by primary key."""
    return db.get(CodeChange, change_id)


def get_code_change_provenance(
    db: Session,
    change_id: UUID,
) -> CodeChangeProvenanceResponse | None:
    """
    Construct the full provenance graph for a single code change.

    Performs multi-table lookups to fetch:
      - The associated GitCommit (if committed)
      - The associated AIInteraction (if AI-assisted)
      - The associated Decision with its Alternatives and Evidence (if recorded)

    Missing links remain explicitly None.
    """
    change = db.get(CodeChange, change_id)
    if change is None:
        return None

    # 1. Fetch Commit if linked
    commit_summary = None
    if change.commit_id is not None:
        commit = db.get(GitCommit, change.commit_id)
        if commit is not None:
            commit_summary = CommitSummary.model_validate(commit)

    # 2. Fetch AI Interaction if linked
    interaction_summary = None
    if change.interaction_id is not None:
        interaction = db.get(AIInteraction, change.interaction_id)
        if interaction is not None:
            interaction_summary = InteractionSummary.model_validate(interaction)

    # 3. Fetch Decision with Alternatives and Evidence if linked
    decision_summary = None
    if change.decision_id is not None:
        decision = db.get(Decision, change.decision_id)
        if decision is not None:
            # Query child alternatives
            alts = list(
                db.scalars(
                    select(Alternative)
                    .where(Alternative.decision_id == decision.decision_id)
                    .order_by(Alternative.alternative_id.asc())
                ).all()
            )
            # Query child evidence
            evidences = list(
                db.scalars(
                    select(Evidence)
                    .where(Evidence.decision_id == decision.decision_id)
                    .order_by(Evidence.captured_at.asc())
                ).all()
            )

            decision_summary = DecisionSummary(
                decision_id=decision.decision_id,
                title=decision.title,
                description=decision.description,
                decision_type=decision.decision_type,
                status=decision.status,
                reason_text=decision.reason_text,
                reason_source_type=decision.reason_source_type,
                reason_confidence=decision.reason_confidence,
                decided_at=decision.decided_at,
                alternatives=[AlternativeSummary.model_validate(a) for a in alts],
                evidence=[EvidenceSummary.model_validate(e) for e in evidences],
            )

    return CodeChangeProvenanceResponse(
        change_id=change.change_id,
        project_id=change.project_id,
        file_path=change.file_path,
        change_type=change.change_type,
        origin=change.origin,
        confidence=change.confidence,
        lines_added=change.lines_added,
        lines_deleted=change.lines_deleted,
        line_start=change.line_start,
        line_end=change.line_end,
        changed_at=change.changed_at,
        commit=commit_summary,
        interaction=interaction_summary,
        decision=decision_summary,
    )


def update_code_change_provenance(
    db: Session,
    change: CodeChange,
    update_data: CodeChangeUpdate,
) -> CodeChange:
    """
    Update provenance links on an existing code change.

    Enforces that referenced interaction or decision belongs to the same project.
    """
    changes = update_data.model_dump(exclude_unset=True)

    # Validate interaction belongs to same project
    if "interaction_id" in changes and changes["interaction_id"] is not None:
        interaction = db.scalar(
            select(AIInteraction).where(
                AIInteraction.interaction_id == changes["interaction_id"],
                AIInteraction.project_id == change.project_id,
            )
        )
        if interaction is None:
            raise ValueError(
                "Referenced AI interaction does not exist in this project."
            )

    # Validate decision belongs to same project
    if "decision_id" in changes and changes["decision_id"] is not None:
        decision = db.scalar(
            select(Decision).where(
                Decision.decision_id == changes["decision_id"],
                Decision.project_id == change.project_id,
            )
        )
        if decision is None:
            raise ValueError(
                "Referenced decision does not exist in this project."
            )

    try:
        for field, value in changes.items():
            setattr(change, field, value)

        db.flush()
        db.commit()
        db.refresh(change)
        return change

    except SQLAlchemyError:
        db.rollback()
        raise


def list_project_code_changes(
    db: Session,
    project_id: UUID,
    missing_provenance_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[CodeChange]:
    """
    List code changes in a project, optionally filtered to unattributed changes.

    When missing_provenance_only=True, this query utilizes the partial index
    'idx_code_change_missing_provenance' for fast reporting.
    """
    statement = (
        select(CodeChange)
        .where(CodeChange.project_id == project_id)
        .order_by(desc(CodeChange.changed_at), CodeChange.change_id)
        .limit(limit)
        .offset(offset)
    )

    if missing_provenance_only:
        statement = statement.where(
            CodeChange.interaction_id.is_(None),
            CodeChange.decision_id.is_(None),
        )

    return list(db.scalars(statement).all())