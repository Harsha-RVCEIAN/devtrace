
"""
DevTrace project API schemas.

This module defines the request and response formats for project-related
API operations. SQLAlchemy models describe how project records are stored
in PostgreSQL, while these Pydantic schemas validate incoming client data
and control which fields are returned by the API.

ProjectCreate validates data supplied when creating a project.
ProjectUpdate validates partial changes to an existing project.
ProjectResponse defines the public representation of a project, including
its UUID and creation timestamp.

Pydantic validates incoming data before it reaches the service layer.
The service layer remains responsible for database operations, project
membership rules, and transaction management.
"""

from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class ProjectCreate(BaseModel):
    """
    Validate the request body used to create a project.

    Clients provide the project name and may optionally provide a description
    and repository URL. Database-generated fields such as project_id and
    created_at are deliberately excluded from this request schema.
    """

    # Require a non-empty project name and remove accidental surrounding
    # whitespace before the data reaches the service layer.
    project_name: str = Field(
        min_length=1,
        description="Human-readable name of the project.",
        examples=["DevTrace"],
    )

    # Description is optional because a project can be created before
    # its purpose or documentation has been finalized.
    description: str | None = Field(
        default=None,
        description="Optional description of the project.",
    )

    # HttpUrl validates that a supplied repository address is a valid URL.
    # None allows a project to exist before its repository is configured.
    repository_url: HttpUrl | None = Field(
        default=None,
        description="Optional URL of the project's source-code repository.",
        examples=["https://github.com/example/devtrace"],
    )

    # Reject unknown request fields to catch spelling mistakes and prevent
    # clients from supplying fields that this operation does not support.
    model_config = ConfigDict(extra="forbid")

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, value: str) -> str:
        """Reject names containing only whitespace."""
        value = value.strip()

        if not value:
            raise ValueError("Project name must not be empty or whitespace.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        """Convert whitespace-only descriptions to None."""
        if value is not None:
            value = value.strip()

            if not value:
                return None

        return value


class ProjectUpdate(BaseModel):
    """
    Validate partial updates to an existing project.

    All fields are optional because a client may want to update only one
    attribute. The route or service should use model_dump(exclude_unset=True)
    so omitted fields remain unchanged in the database.

    An explicitly supplied null description or repository_url can clear that
    value. project_name cannot be null when supplied.
    """

    project_name: str | None = Field(
        default=None,
        min_length=1,
        description="New project name, if it should be changed.",
    )

    description: str | None = Field(
        default=None,
        description="New description, or null to clear the description.",
    )

    repository_url: HttpUrl | None = Field(
        default=None,
        description="New repository URL, or null to clear it.",
    )

    # The API should not silently accept unsupported update fields.
    model_config = ConfigDict(extra="forbid")

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, value: str | None) -> str | None:
        """Reject an empty project name when the field is supplied."""
        if value is None:
            raise ValueError("Project name cannot be null.")

        value = value.strip()

        if not value:
            raise ValueError("Project name must not be empty or whitespace.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        """Normalize whitespace-only descriptions to None."""
        if value is not None:
            value = value.strip()

            if not value:
                return None

        return value

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """
        Reject an update request that contains no fields.

        Pydantic distinguishes an omitted field from a field explicitly
        supplied as null. model_fields_set records which fields the client
        actually included in the request.
        """
        if not self.model_fields_set:
            raise ValueError("At least one project field must be supplied.")

        return self


class ProjectResponse(BaseModel):
    """
    Define the project representation returned by the API.

    This schema includes the database-generated project UUID and creation
    timestamp. from_attributes=True allows Pydantic to build the response
    directly from a SQLAlchemy Project instance without manually constructing
    a dictionary.

    The repository URL is returned as a string so the response matches the
    stored database representation.
    """

    project_id: UUID = Field(
        description="Unique identifier of the project.",
    )

    project_name: str = Field(
        description="Human-readable name of the project.",
    )

    description: str | None = Field(
        description="Optional project description.",
    )

    repository_url: str | None = Field(
        description="Optional source-code repository URL.",
    )

    created_at: datetime = Field(
        description="Timestamp when the project was created.",
    )

    # Enable serialization from ORM object attributes, rather than requiring
    # the service layer to manually copy every field into a dictionary.
    model_config = ConfigDict(from_attributes=True)


class TimelineEventResponse(BaseModel):
    """Activity event in a project's chronological development history."""

    model_config = ConfigDict(from_attributes=True)

    event_id: UUID = Field(description="Identifier of the event.")
    event_type: Literal["interaction", "decision", "commit"] = Field(
        description="Category of the event."
    )
    timestamp: datetime = Field(description="Timestamp when event occurred.")
    title: str = Field(description="Summary title of the event.")
    actor_id: UUID | None = Field(default=None, description="User who triggered event.")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Metadata details."
    )

