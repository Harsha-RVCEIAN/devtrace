"""
app/services/github_sync_service.py

Services for listing GitHub repositories, importing a repo as a DevTrace Project
(with write-verified collaborative join or isolated creation), syncing commits
idempotently into git_commit + code_change, and explicit member invites.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_oauth_token
from app.models.entities import GitCommit, OAuthAccount, Project, ProjectMember, User
from app.schemas.commit import ChangeType, CodeChangeItem, CommitCreate
from app.services.commit_service import ingest_commit_with_changes
from integrations.github.client import (
    get_commit_detail,
    get_repo,
    list_repo_commits,
    parse_github_repo_slug,
)


class GitHubNotLinkedError(Exception):
    """Raised when the user has not linked a GitHub account with an API token."""


class ProjectAccessError(Exception):
    """Raised when a project does not exist or the user lacks required permissions."""


class InviteTargetNotFoundError(Exception):
    """Raised when an invited email or GitHub username does not match a DevTrace user."""


_GITHUB_STATUS_MAP: dict[str, ChangeType] = {
    "added": "added",
    "modified": "modified",
    "removed": "deleted",
    "renamed": "renamed",
    "copied": "added",
    "changed": "modified",
}


def map_github_file_status(gh_status: str | None) -> ChangeType:
    """Map GitHub file status strings to DevTrace's ChangeType enum."""
    if not gh_status:
        return "modified"
    return _GITHUB_STATUS_MAP.get(gh_status.lower(), "modified")


def get_github_token(db: Session, user_id: UUID) -> str:
    """Fetch and decrypt the user's stored GitHub OAuth access token."""
    oauth = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == "github",
        )
    )
    if oauth is None or not oauth.access_token_encrypted:
        raise GitHubNotLinkedError("GitHub account is not connected. Sign in with GitHub to sync repositories.")

    return decrypt_oauth_token(
        oauth.access_token_encrypted,
        settings.auth_secret_key.get_secret_value(),
    )


def import_github_repo(
    db: Session,
    user: User,
    *,
    repo_input: str,
    sync_limit: int = 20,
) -> dict:
    """
    Import a GitHub repository as a DevTrace Project and optionally sync recent commits.

    Membership resolution:
    1. User already belongs to a Project with this repository_url -> reuse it ("existing").
    2. User has GitHub push/admin access (permissions.push) AND a Project with this
       repository_url already exists -> auto-join as member ("write_verified_join").
    3. Otherwise -> create a new isolated Project with user as owner ("created").
    """
    token = get_github_token(db, user.user_id)
    owner, repo_name = parse_github_repo_slug(repo_input)
    repo_meta = get_repo(token, owner, repo_name)

    canonical_url = repo_meta["html_url"].rstrip("/")
    can_push = bool((repo_meta.get("permissions") or {}).get("push", False))

    # 1. Already a member of a project for this repo?
    existing_member_project = db.scalar(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.project_id)
        .where(
            ProjectMember.user_id == user.user_id,
            Project.repository_url == canonical_url,
        )
    )

    if existing_member_project is not None:
        project = existing_member_project
        membership_mode = "existing"
    else:
        # 2. Write-verified join if another teammate already imported this repo
        shared_project = (
            db.scalar(select(Project).where(Project.repository_url == canonical_url))
            if can_push
            else None
        )
        if shared_project is not None:
            db.add(
                ProjectMember(
                    project_id=shared_project.project_id,
                    user_id=user.user_id,
                    role="member",
                )
            )
            db.commit()
            project = shared_project
            membership_mode = "write_verified_join"
        else:
            # 3. Create new isolated project
            project = Project(
                project_name=repo_meta["full_name"],
                description=repo_meta.get("description"),
                repository_url=canonical_url,
            )
            db.add(project)
            db.flush()
            db.add(
                ProjectMember(
                    project_id=project.project_id,
                    user_id=user.user_id,
                    role="owner",
                )
            )
            db.commit()
            db.refresh(project)
            membership_mode = "created"

    sync_stats = (
        sync_project_commits(db, user, project_id=project.project_id, limit=sync_limit)
        if sync_limit > 0
        else {"synced_commits": 0, "skipped_commits": 0, "total_changes": 0}
    )

    return {
        "project_id": project.project_id,
        "project_name": project.project_name,
        "repository_url": canonical_url,
        "membership_mode": membership_mode,
        **sync_stats,
    }


def sync_project_commits(
    db: Session,
    user: User,
    *,
    project_id: UUID,
    limit: int = 20,
) -> dict:
    """Pull recent commits and file changes from GitHub for a project idempotently."""
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.user_id,
        )
    )
    if membership is None:
        raise ProjectAccessError("Project not found.")

    project = db.scalar(select(Project).where(Project.project_id == project_id))
    if project is None or not project.repository_url:
        raise ProjectAccessError("Project has no linked GitHub repository URL.")

    token = get_github_token(db, user.user_id)
    owner, repo_name = parse_github_repo_slug(project.repository_url)

    commits_summary = list_repo_commits(token, owner, repo_name, per_page=limit)
    if not commits_summary:
        return {"project_id": project_id, "synced_commits": 0, "skipped_commits": 0, "total_changes": 0}

    existing_hashes = set(
        db.scalars(
            select(GitCommit.commit_hash).where(GitCommit.project_id == project_id)
        ).all()
    )

    synced = 0
    skipped = 0
    total_changes = 0

    for item in reversed(commits_summary):
        sha = item["sha"]
        if sha in existing_hashes:
            skipped += 1
            continue

        detail = get_commit_detail(token, owner, repo_name, sha)
        commit_info = detail.get("commit", {})
        author_info = commit_info.get("author") or {}
        raw_date = author_info.get("date")
        commit_time = (
            datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if raw_date
            else datetime.now(timezone.utc)
        )
        message = (commit_info.get("message") or "").strip() or f"Commit {sha[:7]}"

        changes: list[CodeChangeItem] = []
        for f in detail.get("files") or []:
            filename = (f.get("filename") or "").strip()
            if not filename:
                continue
            changes.append(
                CodeChangeItem(
                    file_path=filename,
                    change_type=map_github_file_status(f.get("status")),
                    origin="human",
                    lines_added=f.get("additions", 0),
                    lines_deleted=f.get("deletions", 0),
                )
            )

        payload = CommitCreate(
            project_id=project_id,
            commit_hash=sha,
            message=message,
            commit_time=commit_time,
            changes=changes,
        )
        ingest_commit_with_changes(db, payload, user_id=user.user_id)
        existing_hashes.add(sha)
        synced += 1
        total_changes += len(changes)

    return {
        "project_id": project_id,
        "synced_commits": synced,
        "skipped_commits": skipped,
        "total_changes": total_changes,
    }


def invite_project_member(
    db: Session,
    current_user: User,
    *,
    project_id: UUID,
    identifier: str,
    role: str = "member",
) -> tuple[ProjectMember, User]:
    """Explicitly add a DevTrace user (by email or GitHub username) to a project."""
    caller_membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.user_id,
        )
    )
    if caller_membership is None or caller_membership.role != "owner":
        raise ProjectAccessError("Project not found or owner permissions required.")

    cleaned = identifier.strip()
    target_user = db.scalar(select(User).where(User.email == cleaned.lower()))
    if target_user is None:
        oauth_match = db.scalar(
            select(OAuthAccount).where(
                OAuthAccount.provider == "github",
                OAuthAccount.provider_username == cleaned,
            )
        )
        if oauth_match is not None:
            target_user = db.scalar(select(User).where(User.user_id == oauth_match.user_id))

    if target_user is None:
        raise InviteTargetNotFoundError(f"No DevTrace user found matching '{cleaned}'.")

    existing = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user.user_id,
        )
    )
    if existing is not None:
        return existing, target_user

    member = ProjectMember(project_id=project_id, user_id=target_user.user_id, role=role)
    db.add(member)
    db.commit()
    return member, target_user
