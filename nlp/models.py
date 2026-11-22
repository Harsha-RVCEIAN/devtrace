"""
nlp/models.py

The data shapes shared by every part of the NLP pipeline.

Reading guide (from raw input to final output):

    Message            one side of a conversation turn (developer prompt OR AI response)
      └─ Sentence      one sentence of a message, numbered across the whole transcript
    Evidence           a verbatim quote (a Sentence) cited as support for something
    Alternative        one option that was discussed, plus its status and its evidence
    CandidateDecision  one proposed decision: what was chosen, why, and what else was considered

Nothing in this file contains logic; it only describes data.
"""

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID


Speaker = Literal["developer", "assistant"]
SelectionStatus = Literal["selected", "rejected", "considered"]
ReasonSourceType = Literal["EXPLICIT", "INFERRED", "UNKNOWN"]

# Why a quote is attached to a decision:
#   context     the question that started the discussion
#   decision    a sentence where the choice was made / recommended / accepted
#   rationale   a sentence that says WHY
#   alternative a sentence that mentions an option and shows its status
EvidenceRole = Literal["context", "decision", "rationale", "alternative"]


@dataclass(frozen=True)
class Message:
    """One side of a conversation turn. `turn` is 1-based, as shown in the UI."""

    turn: int
    speaker: Speaker
    text: str


@dataclass(frozen=True)
class Sentence:
    """
    One sentence of the transcript.

    `id` is a global position (0, 1, 2, ...) across the whole conversation, so
    "the next sentence" is simply id + 1, even across a message boundary.
    """

    id: int
    turn: int
    speaker: Speaker
    text: str
    is_question: bool = False
    is_bullet: bool = False
    # Index of the message this sentence came from (0-based, in transcript order).
    message_index: int = 0


@dataclass
class Evidence:
    """A verbatim quote from the conversation, and why it was cited."""

    role: EvidenceRole
    turn: int
    speaker: Speaker
    quote: str
    sentence_id: int

    @classmethod
    def from_sentence(cls, sentence: Sentence, role: EvidenceRole) -> "Evidence":
        return cls(
            role=role,
            turn=sentence.turn,
            speaker=sentence.speaker,
            quote=sentence.text,
            sentence_id=sentence.id,
        )


@dataclass
class Alternative:
    """An option discussed for a decision."""

    description: str
    selection_status: SelectionStatus
    # The sentence that best shows this status (None only if nothing could be cited).
    evidence: Evidence | None = None


@dataclass
class CandidateDecision:
    """
    A proposed engineering decision awaiting developer review.

    `status` is ALWAYS "proposed": NLP output is never auto-approved into the
    authoritative DECISION table.
    """

    title: str
    description: str
    decision_type: str
    chosen_option: str
    # How sure we are that a decision was actually made (not WHY it was made).
    confidence: float
    reason_text: str | None = None
    reason_source_type: ReasonSourceType = "UNKNOWN"
    reason_confidence: float = 0.0
    alternatives: list[Alternative] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    status: str = "proposed"
    project_id: UUID | None = None
    interaction_id: UUID | None = None


@dataclass
class ExtractionResult:
    """What the pipeline returns: the candidates plus how they were produced."""

    candidates: list[CandidateDecision]
    engine_used: Literal["rules", "llm"]
    sentences: list[Sentence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
