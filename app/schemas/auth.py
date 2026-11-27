"""Pydantic schemas for authentication and session inspection."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import UserCreate


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return UserCreate.normalize_name(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return UserCreate.normalize_and_validate_email(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return UserCreate.normalize_and_validate_email(value)


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    name: str
    email: str
    role: str
    avatar_url: str | None = None
    created_at: datetime
    linked_providers: list[str] = Field(default_factory=list)
    github_username: str | None = None
