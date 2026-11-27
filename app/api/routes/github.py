"""
app/api/routes/github.py

Routes for listing a user's GitHub repositories, importing a repo as a
DevTrace Project (with write-verified collaborative join), syncing commits,
and explicitly inviting teammates.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.github import (
    GitHubImportRequest,
    GitHubImportResponse,
    GitHubRepoItem,
    GitHubSyncRequest,
    GitHubSyncResponse,
    ProjectMemberInviteRequest,
    ProjectMemberResponse,
)
from app.services.github_sync_service import (
    GitHubNotLinkedError,
    InviteTargetNotFoundError,
    ProjectAccessError,
    get_github_token,
    import_github_repo,
    invite_project_member,
    sync_project_commits,
)
from integrations.github.client import GitHubAPIError, list_user_repos


router = APIRouter(prefix="/github", tags=["GitHub Sync"])


@router.get("/repos", response_model=list[GitHubRepoItem], summary="List user's GitHub repositories")
def get_my_github_repos(current_user: CurrentUser, db: DatabaseSession) -> list[GitHubRepoItem]:
    try:
        token = get_github_token(db, current_user.user_id)
        repos = list_user_repos(token)
    except GitHubNotLinkedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return [
        GitHubRepoItem(
            full_name=r["full_name"],
            name=r["name"],
            private=bool(r.get("private", False)),
            description=r.get("description"),
            html_url=r["html_url"],
            default_branch=r.get("default_branch") or "main",
            can_push=bool((r.get("permissions") or {}).get("push", False)),
        )
        for r in repos
    ]


@router.post(
    "/import",
    response_model=GitHubImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a GitHub repo (owned, collaborator, or public URL) and sync commits",
)
def import_repo(
    payload: GitHubImportRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> GitHubImportResponse:
    try:
        result = import_github_repo(
            db,
            current_user,
            repo_input=payload.repo,
            sync_limit=payload.sync_limit,
        )
        return GitHubImportResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GitHubNotLinkedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/projects/{project_id}/sync",
    response_model=GitHubSyncResponse,
    summary="Pull new commits and code changes from GitHub into a project",
)
def sync_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
    payload: GitHubSyncRequest | None = None,
) -> GitHubSyncResponse:
    limit = payload.limit if payload else 20
    try:
        result = sync_project_commits(db, current_user, project_id=project_id, limit=limit)
        return GitHubSyncResponse(**result)
    except ProjectAccessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitHubNotLinkedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Explicitly invite a DevTrace user to a project by email or GitHub username",
)
def add_member(
    project_id: UUID,
    payload: ProjectMemberInviteRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ProjectMemberResponse:
    try:
        member, target_user = invite_project_member(
            db,
            current_user,
            project_id=project_id,
            identifier=payload.identifier,
            role=payload.role,
        )
        return ProjectMemberResponse(
            project_id=member.project_id,
            user_id=member.user_id,
            name=target_user.name,
            email=target_user.email,
            role=member.role,
        )
    except ProjectAccessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InviteTargetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
