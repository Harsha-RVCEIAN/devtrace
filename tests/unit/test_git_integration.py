"""
tests/unit/test_git_integration.py

Unit tests for Git diff parsing and commit collection.

Tests:
    1. Parsing of git diff --name-status (added, modified, deleted, renamed).
    2. Parsing of git diff --numstat (normal text files and binary files).
    3. End-to-end changeset assembly.
    4. Live collection against the current Git repository HEAD.
"""

import pytest

from integrations.git.collector import collect_commit_metadata
from integrations.git.diff_parser import (
    parse_git_diff_tree,
    parse_name_status_line,
    parse_numstat_output,
)


def test_parse_name_status_line():
    """Verify mapping of git status characters to DevTrace change types."""
    assert parse_name_status_line("M\tsrc/auth.py") == ("modified", "src/auth.py")
    assert parse_name_status_line("A\ttests/test_auth.py") == ("added", "tests/test_auth.py")
    assert parse_name_status_line("D\tdocs/old_plan.md") == ("deleted", "docs/old_plan.md")
    # For renames, file_path must be the new destination path
    assert parse_name_status_line("R100\told_name.py\tnew_name.py") == ("renamed", "new_name.py")


def test_parse_numstat_output():
    """Verify parsing of lines added and deleted, including binary files."""
    sample_output = (
        "42\t10\tsrc/auth.py\n"
        "5\t0\tREADME.md\n"
        "-\t-\tassets/diagram.png\n"
    )
    stats = parse_numstat_output(sample_output)

    assert stats["src/auth.py"] == (42, 10)
    assert stats["README.md"] == (5, 0)
    # Binary file returns (None, None)
    assert stats["assets/diagram.png"] == (None, None)


def test_parse_git_diff_tree_combined():
    """Verify combining name-status and numstat into full CodeChangeItem dicts."""
    name_status = (
        "M\tsrc/auth.py\n"
        "A\tdocs/api.md\n"
    )
    numstat = (
        "15\t3\tsrc/auth.py\n"
        "20\t0\tdocs/api.md\n"
    )

    changes = parse_git_diff_tree(name_status, numstat)

    assert len(changes) == 2

    auth_change = changes[0]
    assert auth_change["file_path"] == "src/auth.py"
    assert auth_change["change_type"] == "modified"
    assert auth_change["lines_added"] == 15
    assert auth_change["lines_deleted"] == 3
    assert auth_change["origin"] == "human"

    doc_change = changes[1]
    assert doc_change["file_path"] == "docs/api.md"
    assert doc_change["change_type"] == "added"
    assert doc_change["lines_added"] == 20
    assert doc_change["lines_deleted"] == 0


def test_parse_empty_diff():
    """Verify empty diff outputs return an empty list without error."""
    assert parse_git_diff_tree("", "") == []


def test_live_git_collection_on_current_repo():
    """Verify that collect_commit_metadata runs real git commands on this repo."""
    meta = collect_commit_metadata(repo_path=".", commit_ref="HEAD")

    assert "commit_hash" in meta
    # SHA-1 hash is 40 hex characters
    assert len(meta["commit_hash"]) >= 7
    assert all(c in "0123456789abcdef" for c in meta["commit_hash"])

    assert "author_name" in meta
    assert len(meta["author_name"]) > 0

    assert "author_email" in meta
    assert "message" in meta
    assert "changes" in meta
    assert isinstance(meta["changes"], list)