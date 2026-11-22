"""
app/schemas/nlp.py

Pydantic schemas for the NLP candidate extraction pipeline and API endpoints.
All schemas enable `from_attributes=True` so internal dataclasses serialize directly.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


EvidenceRole = Literal["context", "decision", "rationale", "alternative"]
Speaker = Literal["developer", "assistant"]
SelectionStatus = Literal["selected", "rejected", "considered"]
ReasonSourceType = Literal["EXPLICIT", "INFERRED", "UNKNOWN"]


class EvidenceResponse(BaseModel):
    """A verbatim quote cited as evidence for a decision, rationale, or alternative."""

    model_config = ConfigDict(from_attributes=True)

    role: EvidenceRole
    turn: int
    speaker: Speaker
    quote: str
    sentence_id: int


class AlternativeResponse(BaseModel):
    """An option considered during an architectural decision."""

    model_config = ConfigDict(from_attributes=True)

    description: str
    selection_status: SelectionStatus
    evidence: EvidenceResponse | None = None


class CandidateDecisionResponse(BaseModel):
    """A proposed architectural decision extracted from a conversation transcript."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    decision_type: str
    chosen_option: str
    confidence: float
    reason_text: str | None = None
    reason_source_type: ReasonSourceType = "UNKNOWN"
    reason_confidence: float = 0.0
    alternatives: list[AlternativeResponse] = Field(default_factory=list)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    status: str = "proposed"
    project_id: UUID | None = None
    interaction_id: UUID | None = None


class ExtractionResponse(BaseModel):
    """The complete response from the decision extraction pipeline."""

    model_config = ConfigDict(from_attributes=True)

    engine_used: Literal["rules", "llm"]
    candidates: list[CandidateDecisionResponse]
    warnings: list[str] = Field(default_factory=list)


class TurnInput(BaseModel):
    """A single developer-assistant conversation turn."""

    prompt: str = ""
    response: str = ""


class NLPExtractCandidatesRequest(BaseModel):
    """Request payload for multi-turn candidate decision extraction."""

    turns: list[TurnInput] = Field(..., min_length=1)
    engine: Literal["rules", "llm", "auto"] = "rules"
    project_id: UUID | None = None
