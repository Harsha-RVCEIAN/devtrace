"""Pydantic schemas for single and batch AI transcript ingestion."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.code_change import CodeChangeProvenanceResponse
from app.schemas.decision import DecisionResponse
from app.schemas.nlp import TurnInput


class IngestTranscriptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(default="AI Chat", min_length=1, max_length=80)
    model_name: str | None = Field(default=None, max_length=120)
    external_session_ref: str | None = Field(default=None, max_length=255)
    engine: Literal["rules", "llm", "auto"] = "rules"
    turns: list[TurnInput] | None = None
    raw_text: str | None = None
    commit_id: UUID | None = None
    auto_link: bool = True
    auto_approve: bool = True

    @model_validator(mode="after")
    def validate_source_supplied(self) -> "IngestTranscriptRequest":
        has_turns = bool(self.turns and len(self.turns) > 0)
        has_raw = bool(self.raw_text and self.raw_text.strip())
        if not has_turns and not has_raw:
            raise ValueError("Provide either non-empty 'turns' or 'raw_text'.")
        return self


class IngestTranscriptResponse(BaseModel):
    interaction_id: UUID
    turns_count: int
    engine_used: str
    warnings: list[str] = Field(default_factory=list)
    staged_decisions: list[DecisionResponse] = Field(default_factory=list)
    auto_linked_changes: list[CodeChangeProvenanceResponse] = Field(default_factory=list)


class BatchTranscriptItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(default="AI Chat", min_length=1, max_length=80)
    model_name: str | None = Field(default=None, max_length=120)
    turns: list[TurnInput]
    commit_id: UUID | None = None


class BatchIngestTranscriptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    engine: Literal["rules", "llm", "auto"] = "rules"
    tool_name: str = Field(default="AI Chat", min_length=1, max_length=80)
    model_name: str | None = Field(default=None, max_length=120)
    raw_text: str | None = None
    conversations: list[BatchTranscriptItem] | None = None
    auto_link: bool = True
    auto_approve: bool = True

    @model_validator(mode="after")
    def validate_batch_source(self) -> "BatchIngestTranscriptRequest":
        has_convs = bool(self.conversations and len(self.conversations) > 0)
        has_raw = bool(self.raw_text and self.raw_text.strip())
        if not has_convs and not has_raw:
            raise ValueError("Provide either non-empty 'conversations' or 'raw_text'.")
        return self


class BatchIngestTranscriptResponse(BaseModel):
    interactions_count: int
    engine_used: str
    warnings: list[str] = Field(default_factory=list)
    staged_decisions: list[DecisionResponse] = Field(default_factory=list)
    auto_linked_changes: list[CodeChangeProvenanceResponse] = Field(default_factory=list)
