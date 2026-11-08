
"""
Pydantic schemas for AI-interaction ingestion and responses.

These schemas define the API contract for recording AI-assisted development
sessions in DevTrace.

Responsibilities:
    - Validate client-supplied interaction data.
    - Require a valid project UUID.
    - Validate tool and model identifiers.
    - Represent prompts, AI responses, and optional external session references.
    - Serialize persisted SQLAlchemy AIInteraction objects into API responses.

Security:
    The client does not supply user_id. The API derives the user identity
    from the existing CurrentUser dependency so that clients cannot choose
    another user's identity in the request body.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InteractionCreate(BaseModel):
    """
    Validate the request body for POST /interactions.

    Attributes:
        project_id: Project to which this AI interaction belongs.
        tool_name: Name of the AI tool used, such as a coding assistant.
        model_name: Model identifier supplied by the client.
        external_session_ref: Optional session identifier from the AI tool.
        prompt: Prompt or input sent to the AI system.
        response: Response received from the AI system.

    The authenticated user's UUID is deliberately excluded. It is supplied
    by the server after resolving the CurrentUser dependency.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
    )

    project_id: UUID = Field(
        ...,
        description="UUID of the project associated with this interaction.",
    )

    tool_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Name of the AI tool used.",
    )

    model_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Identifier of the AI model used.",
    )

    external_session_ref: str | None = Field(
        default=None,
        max_length=500,
        description="Optional session identifier from the external AI tool.",
    )

    prompt: str = Field(
        ...,
        min_length=1,
        description="Prompt or input submitted to the AI tool.",
    )

    response: str = Field(
        ...,
        min_length=1,
        description="Response produced by the AI tool.",
    )

    @field_validator("tool_name", "model_name")
    @classmethod
    def validate_required_identifiers(cls, value: str) -> str:
        """
        Reject identifiers that contain only whitespace.

        Leading and trailing whitespace is removed from tool and model names
        so that stored identifiers remain consistent.
        """
        value = value.strip()

        if not value:
            raise ValueError("This field must not be blank.")

        return value

    @field_validator("external_session_ref")
    @classmethod
    def normalize_external_session_ref(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normalize an optional external session reference.

        An omitted reference or a whitespace-only reference becomes None.
        This avoids storing meaningless empty session identifiers.
        """
        if value is None:
            return None

        value = value.strip()
        return value or None


class InteractionResponse(BaseModel):
    """
    Serialize a persisted AIInteraction ORM object.

    The response contains the server-generated interaction UUID, the
    associated project and user UUIDs, the recorded AI content, and the
    database-generated creation timestamp.

    ConfigDict(from_attributes=True) allows Pydantic to read attributes
    directly from the SQLAlchemy ORM instance.
    """

    model_config = ConfigDict(from_attributes=True)

    interaction_id: UUID
    project_id: UUID
    user_id: UUID
    tool_name: str
    model_name: str
    external_session_ref: str | None
    prompt: str
    response: str
    created_at: datetime
