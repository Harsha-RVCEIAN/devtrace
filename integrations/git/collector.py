"""
integrations/git/collector.py

Purpose:
    Collect Git commit metadata and diff stats from a repository and submit
    them to the DevTrace API.

Usage:
    # 1. Inspect collected payload without sending (dry-run):
    python -m integrations.git.collector --dry-run --project-id <UUID>

    # 2. Ingest HEAD commit to DevTrace API:
    python -m integrations.git.collector \\
        --project-id <UUID> \\
        --user-id <UUID> \\
        --api-url http://localhost:8000/commits
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from integrations.git.diff_parser import parse_git_diff_tree


def _run_git_command(args: list[str], repo_path: str = ".") -> str:
    """Run a git command in the target directory and return stdout."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Git command failed: {' '.join(args)}\nError: {exc.stderr.strip()}"
        ) from exc


def collect_commit_metadata(
    repo_path: str = ".",
    commit_ref: str = "HEAD",
) -> dict[str, Any]:
    """
    Extract commit hash, message, author, timestamp, and diff stats for a commit ref.

    Args:
        repo_path: Path to the local git repository.
        commit_ref: Git reference (e.g. 'HEAD', 'main', or a SHA hash).

    Returns:
        dict[str, Any]: Metadata dictionary with commit and changes list.
    """
    # %H = commit hash, %an = author name, %ae = author email, %aI = ISO date, %B = raw body
    # Using ASCII Unit Separator (\x1f) to split fields safely
    fmt = "%H%x1f%an%x1f%ae%x1f%aI%x1f%B"
    raw_meta = _run_git_command(["log", "-1", f"--format={fmt}", commit_ref], repo_path)

    parts = raw_meta.split("\x1f")
    if len(parts) < 5:
        raise ValueError(f"Unexpected git log format for ref: {commit_ref}")

    commit_hash = parts[0].strip()
    author_name = parts[1].strip()
    author_email = parts[2].strip()
    commit_time = parts[3].strip()
    commit_message = parts[4].strip()

    # Query file changes: name-status and numstat
    # For initial commit or merge commits, diff against root or parent
    name_status = _run_git_command(
        ["diff-tree", "-r", "--no-commit-id", "--name-status", commit_hash],
        repo_path,
    )
    numstat = _run_git_command(
        ["diff-tree", "-r", "--no-commit-id", "--numstat", commit_hash],
        repo_path,
    )

    changes = parse_git_diff_tree(
        name_status_text=name_status,
        numstat_text=numstat,
    )

    return {
        "commit_hash": commit_hash,
        "author_name": author_name,
        "author_email": author_email,
        "commit_time": commit_time,
        "message": commit_message or "No commit message",
        "changes": changes,
    }


def send_commit_to_api(
    payload: dict[str, Any],
    project_id: UUID,
    user_id: UUID,
    api_url: str = "http://localhost:8000/commits",
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Submit collected commit payload to the DevTrace FastAPI backend.

    Args:
        payload: Metadata dictionary from collect_commit_metadata.
        project_id: DevTrace project UUID.
        user_id: DevTrace authenticated user UUID.
        api_url: URL of the DevTrace commit ingestion endpoint.
        timeout: HTTP request timeout in seconds.

    Returns:
        dict[str, Any]: Server response JSON.
    """
    request_body = {
        "project_id": str(project_id),
        "commit_hash": payload["commit_hash"],
        "message": payload["message"],
        "commit_time": payload["commit_time"],
        "changes": payload["changes"],
    }

    headers = {
        "X-User-ID": str(user_id),
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(api_url, json=request_body, headers=headers)
        response.raise_for_status()
        return response.json()


def main() -> None:
    """CLI entrypoint for manual collection or git post-commit hooks."""
    parser = argparse.ArgumentParser(
        description="DevTrace Git Commit Collector: extracts git metadata and submits to DevTrace API."
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to the Git repository (default: current directory).",
    )
    parser.add_argument(
        "--commit-ref",
        default="HEAD",
        help="Git commit ref to inspect (default: HEAD).",
    )
    parser.add_argument(
        "--project-id",
        type=UUID,
        required=True,
        help="UUID of the target DevTrace project.",
    )
    parser.add_argument(
        "--user-id",
        type=UUID,
        help="UUID of the DevTrace user authoring this commit.",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/commits",
        help="URL of the DevTrace API commits endpoint.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print collected payload to stdout without sending to the API.",
    )

    args = parser.parse_args()

    try:
        metadata = collect_commit_metadata(
            repo_path=args.repo_path,
            commit_ref=args.commit_ref,
        )

        if args.dry_run:
            print("=== DevTrace Git Collector (Dry Run) ===")
            print(f"Project ID: {args.project_id}")
            print(f"Commit: {metadata['commit_hash']}")
            print(f"Author: {metadata['author_name']} <{metadata['author_email']}>")
            print(f"Files Changed: {len(metadata['changes'])}")
            print("\nPayload:")
            print(json.dumps(metadata, indent=2))
            return

        if not args.user_id:
            sys.exit("Error: --user-id is required when not in --dry-run mode.")

        print(f"Submitting commit {metadata['commit_hash'][:8]} to {args.api_url}...")
        res = send_commit_to_api(
            payload=metadata,
            project_id=args.project_id,
            user_id=args.user_id,
            api_url=args.api_url,
        )
        print(f"Successfully recorded commit! Commit ID: {res.get('commit_id')}")

    except Exception as exc:
        sys.exit(f"DevTrace Git Collector Error: {exc}")


if __name__ == "__main__":
    main()