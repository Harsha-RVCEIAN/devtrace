
"""
Pydantic schemas for engineering decision management.

Responsibilities:
    - Validate decision creation and update requests.
    - Enforce the status and reason-source values supported by the ORM.
    - Validate confidence values.
    - Serialize Decision ORM instances into API responses.

The schemas validate request shape and field-level rules. Project membership,
referential integrity, and same-project constraints are handled by the service
layer, API routes, and database constraints.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


DecisionStatus = Literal["proposed", "active", "replaced", "rejected"]
ReasonSourceType = Literal["EXPLICIT", "INFERRED", "UNKNOWN"]


class DecisionCreate(BaseModel):
    """Request body for creating an engineering decision."""

    model_config = ConfigDict(extra="forbid")

    # Optional link to the AI interaction that informed this decision.
    interaction_id: UUID | None = Field(
        default=None,
        description="Optional AI interaction associated with this decision.",
    )

    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1)
    decision_type: str = Field(..., min_length=1, max_length=80)

    # New decisions start as proposed unless the caller specifies otherwise.
    status: DecisionStatus = "proposed"

    reason_text: str | None = None
    reason_source_type: ReasonSourceType = "UNKNOWN"
    reason_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    decided_at: datetime | None = None

    @field_validator("title", "description", "decision_type")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        """Reject strings containing only whitespace."""
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank.")
        return value

    @field_validator("reason_text")
    @classmethod
    def normalize_reason_text(cls, value: str | None) -> str | None:
        """Convert blank optional reason text to None."""
        if value is None:
            return None
        value = value.strip()
        return value or None


class DecisionUpdate(BaseModel):
    """
    Request body for updating an existing decision.

    Only explicitly supplied fields are updated. Project ownership and
    primary-key fields are intentionally excluded from this schema.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = Field(default=None, min_length=1)
    decision_type: str | None = Field(default=None, min_length=1, max_length=80)
    status: DecisionStatus | None = None
    reason_text: str | None = None
    reason_source_type: ReasonSourceType | None = None
    reason_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    interaction_id: UUID | None = None
    replaced_by_decision_id: UUID | None = None
    decided_at: datetime | None = None

    @field_validator("title", "description", "decision_type")
    @classmethod
    def reject_blank_updated_text(cls, value: str | None) -> str | None:
        """Reject explicitly supplied blank required-text fields."""
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank.")
        return value

    @field_validator("reason_text")
    @classmethod
    def normalize_updated_reason(cls, value: str | None) -> str | None:
        """Normalize blank reason text to None."""
        if value is None:
            return None
        value = value.strip()
        return value or None

    def ensure_non_empty_update(self) -> "DecisionUpdate":
        """Reject update requests that contain no fields."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied.")
        return self


class DecisionResponse(BaseModel):
    """Response schema for a persisted decision."""

    model_config = ConfigDict(from_attributes=True)

    decision_id: UUID
    project_id: UUID
    interaction_id: UUID | None
    replaced_by_decision_id: UUID | None
    title: str
    description: str
    decision_type: str
    status: DecisionStatus
    reason_text: str | None
    reason_source_type: ReasonSourceType
    reason_confidence: float | None
    decided_at: datetime | None
