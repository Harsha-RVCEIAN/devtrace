"""Unit tests for GitHub repo slug parsing, status mapping, import isolation, and idempotent sync."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.github_sync_service import (
    import_github_repo,
    map_github_file_status,
    sync_project_commits,
)
from integrations.github.client import parse_github_repo_slug


def test_parse_github_repo_slug():
    assert parse_github_repo_slug("octocat/hello-world") == ("octocat", "hello-world")
    assert parse_github_repo_slug("https://github.com/octocat/hello-world") == ("octocat", "hello-world")
    assert parse_github_repo_slug("https://github.com/octocat/hello-world.git/") == ("octocat", "hello-world")

    with pytest.raises(ValueError):
        parse_github_repo_slug("invalid-slug")


def test_map_github_file_status():
    assert map_github_file_status("added") == "added"
    assert map_github_file_status("modified") == "modified"
    assert map_github_file_status("removed") == "deleted"
    assert map_github_file_status("renamed") == "renamed"


def test_import_write_verified_join_vs_isolated_create():
    user = SimpleNamespace(user_id=uuid4(), name="Teammate", email="team@example.com")
    existing_proj = SimpleNamespace(
        project_id=uuid4(),
        project_name="org/shared-repo",
        repository_url="https://github.com/org/shared-repo",
    )

    # Case 1: User has push permission -> write_verified_join onto existing_proj
    mock_db = MagicMock()
    mock_db.scalar.side_effect = [None, existing_proj]
    with (
        patch("app.services.github_sync_service.get_github_token", return_value="tok"),
        patch(
            "app.services.github_sync_service.get_repo",
            return_value={
                "full_name": "org/shared-repo",
                "html_url": "https://github.com/org/shared-repo",
                "description": "Shared",
                "permissions": {"pull": True, "push": True},
            },
        ),
    ):
        res = import_github_repo(mock_db, user, repo_input="org/shared-repo", sync_limit=0)
    assert res["membership_mode"] == "write_verified_join"
    assert res["project_id"] == existing_proj.project_id

    # Case 2: Public repo where user does NOT have push permission -> isolated "created" project
    mock_db_no_push = MagicMock()
    mock_db_no_push.scalar.side_effect = [None]
    with (
        patch("app.services.github_sync_service.get_github_token", return_value="tok"),
        patch(
            "app.services.github_sync_service.get_repo",
            return_value={
                "full_name": "torvalds/linux",
                "html_url": "https://github.com/torvalds/linux",
                "description": "Kernel",
                "permissions": {"pull": True, "push": False},
            },
        ),
    ):
        res2 = import_github_repo(mock_db_no_push, user, repo_input="https://github.com/torvalds/linux", sync_limit=0)
    assert res2["membership_mode"] == "created"


def test_sync_project_commits_skips_existing_hashes():
    user = SimpleNamespace(user_id=uuid4())
    pid = uuid4()
    project = SimpleNamespace(project_id=pid, repository_url="https://github.com/a/b")
    membership = SimpleNamespace(project_id=pid, user_id=user.user_id, role="owner")

    existing_sha = "a" * 40
    new_sha = "b" * 40

    mock_db = MagicMock()
    mock_db.scalar.side_effect = [membership, project]
    mock_db.scalars.return_value.all.return_value = [existing_sha]

    commits_list = [
        {"sha": new_sha},
        {"sha": existing_sha},
    ]
    commit_detail = {
        "sha": new_sha,
        "commit": {
            "message": "feat: add auth",
            "author": {"date": "2026-11-27T12:00:00Z"},
        },
        "files": [
            {"filename": "app/auth.py", "status": "added", "additions": 50, "deletions": 0},
            {"filename": "old.py", "status": "removed", "additions": 0, "deletions": 12},
        ],
    }

    with (
        patch("app.services.github_sync_service.get_github_token", return_value="tok"),
        patch("app.services.github_sync_service.list_repo_commits", return_value=commits_list),
        patch("app.services.github_sync_service.get_commit_detail", return_value=commit_detail),
        patch("app.services.github_sync_service.ingest_commit_with_changes") as mock_ingest,
    ):
        stats = sync_project_commits(mock_db, user, project_id=pid, limit=20)

    assert stats["synced_commits"] == 1
    assert stats["skipped_commits"] == 1
    assert stats["total_changes"] == 2
    mock_ingest.assert_called_once()
