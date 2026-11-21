"""
app/schemas/commit.py

Purpose:
    Pydantic schemas for Git commit and code-change ingestion.

Responsibilities:
    - Validate commit hash format, commit message, and commit timestamp.
    - Validate nested code changes (file path, change type, origin, line counts).
    - Enforce origin allowed values ('ai_exact', 'ai_inferred', 'human').
    - Validate confidence ranges (0.0 to 1.0).
    - Serialize persisted GitCommit and CodeChange records into API responses.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


CodeChangeOrigin = Literal["ai_exact", "ai_inferred", "human"]
ChangeType = Literal["added", "modified", "deleted", "renamed"]


class CodeChangeItem(BaseModel):
    """
    Validate a single file change included in a Git commit payload.

    Attributes:
        file_path: Relative repository file path (e.g. 'src/main.py').
        change_type: Action performed on the file.
        origin: Provenance of this change ('human', 'ai_inferred', 'ai_exact').
        confidence: Confidence score (0.0 to 1.0), required for 'ai_inferred'.
        lines_added: Count of added lines (>= 0).
        lines_deleted: Count of deleted lines (>= 0).
        line_start: Optional starting line number in the file (>= 1).
        line_end: Optional ending line number in the file (>= 1).
        interaction_id: Optional UUID of the AI interaction that inspired this change.
        decision_id: Optional UUID of the engineering decision driving this change.
    """

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., min_length=1, max_length=1000)
    change_type: ChangeType = "modified"
    origin: CodeChangeOrigin = "human"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    lines_added: int | None = Field(default=None, ge=0)
    lines_deleted: int | None = Field(default=None, ge=0)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    interaction_id: UUID | None = None
    decision_id: UUID | None = None

    @field_validator("file_path")
    @classmethod
    def clean_file_path(cls, value: str) -> str:
        """Strip whitespace and reject blank paths."""
        value = value.strip()
        if not value:
            raise ValueError("file_path must not be blank.")
        return value


class CommitCreate(BaseModel):
    """
    Validate the request body for ingesting a Git commit and its changes.

    Attributes:
        project_id: Project to which this commit belongs.
        commit_hash: 40 or 64 character git commit SHA.
        message: Git commit message.
        commit_time: Timestamp of the git commit.
        changes: Optional list of file changes introduced by this commit.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    commit_hash: str = Field(..., min_length=7, max_length=64)
    message: str = Field(..., min_length=1)
    commit_time: datetime
    changes: list[CodeChangeItem] = Field(default_factory=list)

    @field_validator("commit_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        """Normalize commit hash to lowercase and strip whitespace."""
        value = value.strip().lower()
        if not all(c in "0123456789abcdef" for c in value):
            raise ValueError("commit_hash must be a valid hexadecimal string.")
        return value

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        """Reject empty whitespace messages."""
        value = value.strip()
        if not value:
            raise ValueError("Commit message must not be blank.")
        return value


class CodeChangeResponse(BaseModel):
    """Public representation of a persisted code change."""

    model_config = ConfigDict(from_attributes=True)

    change_id: UUID
    project_id: UUID
    commit_id: UUID | None
    interaction_id: UUID | None
    decision_id: UUID | None
    file_path: str
    change_type: str
    origin: CodeChangeOrigin
    confidence: float | None
    lines_added: int | None
    lines_deleted: int | None
    line_start: int | None
    line_end: int | None
    changed_at: datetime


class CommitResponse(BaseModel):
    """Public representation of a persisted Git commit, including its changes."""

    model_config = ConfigDict(from_attributes=True)

    commit_id: UUID
    project_id: UUID
    user_id: UUID
    commit_hash: str
    message: str
    commit_time: datetime
    changes: list[CodeChangeResponse] = Field(default_factory=list)