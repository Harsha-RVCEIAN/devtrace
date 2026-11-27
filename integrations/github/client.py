"""
integrations/github/client.py

Thin, stateless httpx client for GitHub REST API v3.
Accepts a user's decrypted OAuth access token to list public/private repos,
inspect repo permissions, and fetch commit + file diff metadata.
"""

import re
from typing import Any

import httpx


_GITHUB_API_BASE = "https://api.github.com"
_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHubAPIError(Exception):
    """Raised when GitHub returns an error or unexpected response."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def parse_github_repo_slug(repo_input: str) -> tuple[str, str]:
    """
    Parse 'owner/repo' or 'https://github.com/owner/repo(.git)' into (owner, repo).
    """
    cleaned = repo_input.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    if "github.com/" in cleaned:
        cleaned = cleaned.split("github.com/", 1)[1]

    parts = [p for p in cleaned.split("/") if p]
    if len(parts) < 2:
        raise ValueError("Provide a GitHub repository as 'owner/repo' or a GitHub URL.")

    slug = f"{parts[0]}/{parts[1]}"
    if not _SLUG_RE.match(slug):
        raise ValueError("Invalid GitHub repository name.")

    return parts[0], parts[1]


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_user_repos(access_token: str, per_page: int = 100) -> list[dict[str, Any]]:
    """List repositories the authenticated user owns, collaborates on, or belongs to via orgs."""
    with httpx.Client(timeout=15.0) as client:
        res = client.get(
            f"{_GITHUB_API_BASE}/user/repos",
            headers=_headers(access_token),
            params={
                "sort": "updated",
                "direction": "desc",
                "per_page": min(max(per_page, 1), 100),
                "affiliation": "owner,collaborator,organization_member",
            },
        )
    if res.status_code == 401:
        raise GitHubAPIError("GitHub token expired or revoked. Please sign in again.", status_code=401)
    if res.status_code != 200:
        raise GitHubAPIError(f"GitHub API error ({res.status_code}) while listing repositories.")
    return res.json()


def get_repo(access_token: str, owner: str, repo: str) -> dict[str, Any]:
    """Fetch metadata and caller permissions for a specific repository."""
    with httpx.Client(timeout=15.0) as client:
        res = client.get(
            f"{_GITHUB_API_BASE}/repos/{owner}/{repo}",
            headers=_headers(access_token),
        )
    if res.status_code == 404:
        raise GitHubAPIError(f"Repository '{owner}/{repo}' not found or inaccessible.", status_code=404)
    if res.status_code == 401:
        raise GitHubAPIError("GitHub token expired or revoked.", status_code=401)
    if res.status_code != 200:
        raise GitHubAPIError(f"GitHub API error ({res.status_code}) while fetching '{owner}/{repo}'.")
    return res.json()


def list_repo_commits(
    access_token: str,
    owner: str,
    repo: str,
    *,
    per_page: int = 20,
    sha: str | None = None,
) -> list[dict[str, Any]]:
    """List recent commits on the repository's default (or specified) branch."""
    params: dict[str, Any] = {"per_page": min(max(per_page, 1), 100)}
    if sha:
        params["sha"] = sha

    with httpx.Client(timeout=15.0) as client:
        res = client.get(
            f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            headers=_headers(access_token),
            params=params,
        )
    if res.status_code == 409:
        # GitHub returns 409 for an empty repository with no commits yet
        return []
    if res.status_code != 200:
        raise GitHubAPIError(f"GitHub API error ({res.status_code}) while listing commits.")
    return res.json()


def get_commit_detail(access_token: str, owner: str, repo: str, sha: str) -> dict[str, Any]:
    """Fetch full commit metadata including per-file additions, deletions, and status."""
    with httpx.Client(timeout=15.0) as client:
        res = client.get(
            f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{sha}",
            headers=_headers(access_token),
        )
    if res.status_code != 200:
        raise GitHubAPIError(f"GitHub API error ({res.status_code}) while fetching commit {sha[:7]}.")
    return res.json()
