
"""
DevTrace User Schemas
=====================

Purpose
-------
Defines the Pydantic request and response models used by the user API.
These schemas establish the boundary between untrusted client payloads and
the application's persisted user records.

Request Validation
------------------
UserCreate accepts the fields required to register a user. The name and
email are normalized to avoid storing leading or trailing whitespace, and
email addresses are normalized to lowercase for consistent comparisons.

The client cannot provide the database-generated user UUID, creation
timestamp, or application role. This prevents public registration requests
from directly assigning themselves a privileged role.

Response Serialization
----------------------
UserResponse exposes the user's UUID, name, email, role, and creation
timestamp. ConfigDict(from_attributes=True) allows Pydantic to serialize
the existing SQLAlchemy User entity directly.

Dependencies
------------
- pydantic.BaseModel: request validation and response serialization.
- app.models.entities.User: the persisted user model represented by the
  response schema.

This module does not insert users into the database, check whether an email
is already registered, authenticate users, or grant project permissions.
Those responsibilities belong to the API, database, and authentication
layers.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    """
    Validate the information accepted during user registration.

    Only name and email are accepted. The API assigns the default developer
    role server-side, and the database model generates the user's UUID and
    creation timestamp.

    Attributes:
        name: Display name, limited to 120 characters.
        email: Email address, limited to 320 characters and normalized to
            lowercase after basic format validation.

    Extra fields are forbidden so clients cannot silently submit fields
    such as user_id, created_at, or role.
    """

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """
        Remove surrounding whitespace and reject a blank display name.

        Checking after trimming prevents strings containing only spaces from
        being accepted as valid names.
        """
        value = value.strip()

        if not value:
            raise ValueError("Name must not be blank.")

        return value

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        """
        Normalize email casing and perform basic structural validation.

        This check catches common malformed values but does not prove that
        the address exists or that the user controls its mailbox. A
        production registration flow should verify email ownership.
        """
        value = value.strip().lower()

        if not value or " " in value:
            raise ValueError("Enter a valid email address.")

        if value.count("@") != 1:
            raise ValueError("Enter a valid email address.")

        local_part, domain = value.split("@")

        if not local_part or not domain or "." not in domain:
            raise ValueError("Enter a valid email address.")

        if domain.startswith(".") or domain.endswith("."):
            raise ValueError("Enter a valid email address.")

        return value


class UserResponse(BaseModel):
    """
    Define the public representation of a persisted user.

    The response contains database-generated identity and timestamp fields,
    along with the user's public profile information. It deliberately
    excludes internal credentials and other authentication secrets.

    Attributes:
        user_id: UUID primary key of the persisted user.
        name: User's display name.
        email: Normalized email address.
        role: Application role assigned by trusted server-side logic.
        created_at: Timestamp recording when the user was created.
    """

    user_id: UUID
    name: str
    email: str
    role: str
    created_at: datetime

    # Enables serialization directly from SQLAlchemy model attributes.
    model_config = ConfigDict(from_attributes=True)
