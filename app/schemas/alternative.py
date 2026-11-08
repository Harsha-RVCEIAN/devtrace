
"""
Pydantic schemas for decision alternatives.

These schemas define the API contract for creating, updating, and returning
alternatives associated with a software engineering decision.

The SQLAlchemy Alternative model remains responsible for database-level
constraints. These Pydantic schemas validate incoming API data before it
reaches the service and repository/database layer.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Keep these values synchronized with the CHECK constraint in the ORM model.
AlternativeSelectionStatus = Literal["selected", "rejected", "considered"]


class AlternativeCreate(BaseModel):
    """
    Request schema for creating a decision alternative.

    An alternative belongs to an existing decision. The decision ID is supplied
    in the URL, so it is deliberately not duplicated in this request body.

    Attributes:
        description: Explanation of the proposed alternative.
        selection_status: Whether the alternative was selected, rejected,
            or retained for consideration. Defaults to 'considered'.
    """

    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        min_length=1,
        max_length=10000,
        description="Description of the alternative considered.",
    )

    selection_status: AlternativeSelectionStatus = Field(
        default="considered",
        description="Current selection state of this alternative.",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        """
        Reject whitespace-only descriptions and remove surrounding whitespace.

        A string containing spaces is technically non-empty, so min_length
        alone would not prevent meaningless descriptions.
        """
        value = value.strip()

        if not value:
            raise ValueError("Alternative description cannot be blank.")

        return value


class AlternativeUpdate(BaseModel):
    """
    Request schema for partially updating an existing alternative.

    PATCH semantics are used: clients may update the description, selection
    status, or both. At least one field must be supplied by the API route.

    Explicit null values are rejected for these non-nullable fields.
    """

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
        description="Updated description of the alternative.",
    )

    selection_status: AlternativeSelectionStatus | None = Field(
        default=None,
        description="Updated selection state.",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        """Normalize descriptions and reject blank or null updates."""
        if value is None:
            raise ValueError("Alternative description cannot be null.")

        value = value.strip()

        if not value:
            raise ValueError("Alternative description cannot be blank.")

        return value

    @field_validator("selection_status")
    @classmethod
    def validate_selection_status(
        cls, value: AlternativeSelectionStatus | None
    ) -> AlternativeSelectionStatus:
        """Reject null for the non-nullable database status column."""
        if value is None:
            raise ValueError("Selection status cannot be null.")

        return value


class AlternativeResponse(BaseModel):
    """
    Response schema for an alternative returned by the API.

    from_attributes=True allows Pydantic to serialize SQLAlchemy ORM objects
    without manually converting every field to a dictionary.
    """

    model_config = ConfigDict(from_attributes=True)

    alternative_id: UUID
    decision_id: UUID
    description: str
    selection_status: AlternativeSelectionStatus
