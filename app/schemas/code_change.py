"""
app/schemas/code_change.py

Purpose:
    Pydantic schemas for code change management and full provenance tracing.

Responsibilities:
    - Validate partial provenance updates (linking changes to decisions/interactions).
    - Represent nested provenance graph responses (Change -> Commit, Interaction, Decision).
    - Explicitly represent missing links as None without guessing.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


CodeChangeOrigin = Literal["ai_exact", "ai_inferred", "human"]


class CommitSummary(BaseModel):
    """Summarized Git commit info for provenance responses."""

    model_config = ConfigDict(from_attributes=True)

    commit_id: UUID
    commit_hash: str
    message: str
    commit_time: datetime


class InteractionSummary(BaseModel):
    """Summarized AI interaction info for provenance responses."""

    model_config = ConfigDict(from_attributes=True)

    interaction_id: UUID
    tool_name: str
    model_name: str | None
    prompt: str
    response: str


class AlternativeSummary(BaseModel):
    """Summarized alternative info for decision provenance."""

    model_config = ConfigDict(from_attributes=True)

    alternative_id: UUID
    description: str
    selection_status: str


class EvidenceSummary(BaseModel):
    """Summarized evidence info for decision provenance."""

    model_config = ConfigDict(from_attributes=True)

    evidence_id: UUID
    evidence_type: str
    source_reference: str


class DecisionSummary(BaseModel):
    """Summarized engineering decision with its alternatives and evidence."""

    model_config = ConfigDict(from_attributes=True)

    decision_id: UUID
    title: str
    description: str
    decision_type: str
    status: str
    reason_text: str | None
    reason_source_type: str
    reason_confidence: float | None
    decided_at: datetime | None
    alternatives: list[AlternativeSummary] = Field(default_factory=list)
    evidence: list[EvidenceSummary] = Field(default_factory=list)


class CodeChangeUpdate(BaseModel):
    """
    Validate updates to an existing code change.

    Allows linking an unlinked change to an AI interaction or decision,
    or updating origin and attribution confidence.
    """

    model_config = ConfigDict(extra="forbid")

    interaction_id: UUID | None = None
    decision_id: UUID | None = None
    origin: CodeChangeOrigin | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class CodeChangeProvenanceResponse(BaseModel):
    """
    The complete provenance graph of a code change.

    Missing links remain explicitly None to prevent inventing missing rationale.
    """

    model_config = ConfigDict(from_attributes=True)

    change_id: UUID
    project_id: UUID
    file_path: str
    change_type: str
    origin: CodeChangeOrigin
    confidence: float | None
    lines_added: int | None
    lines_deleted: int | None
    line_start: int | None
    line_end: int | None
    changed_at: datetime

    # The auditable provenance links (None if unlinked / unattributed)
    commit: CommitSummary | None = None
    interaction: InteractionSummary | None = None
    decision: DecisionSummary | None = None