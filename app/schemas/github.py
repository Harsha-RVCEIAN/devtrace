"""Pydantic schemas for GitHub repository listing, import, commit sync, and member invites."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GitHubRepoItem(BaseModel):
    full_name: str
    name: str
    private: bool
    description: str | None = None
    html_url: str
    default_branch: str = "main"
    can_push: bool = False


class GitHubImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo: str = Field(..., min_length=3, max_length=500, description="'owner/repo' or GitHub URL")
    sync_limit: int = Field(default=20, ge=0, le=50)


class GitHubSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=50)


class GitHubSyncResponse(BaseModel):
    project_id: UUID
    synced_commits: int
    skipped_commits: int
    total_changes: int


class GitHubImportResponse(BaseModel):
    project_id: UUID
    project_name: str
    repository_url: str
    membership_mode: str  # "existing" | "write_verified_join" | "created"
    synced_commits: int
    skipped_commits: int
    total_changes: int


class ProjectMemberInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(
        ...,
        min_length=2,
        max_length=320,
        description="Registered user email or GitHub username",
    )
    role: str = Field(default="member", pattern="^(owner|member)$")


class ProjectMemberResponse(BaseModel):
    project_id: UUID
    user_id: UUID
    name: str
    email: str
    role: str
