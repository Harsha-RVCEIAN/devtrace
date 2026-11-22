"""
integrations/git/diff_parser.py

Purpose:
    Parse raw Git diff statistics and status outputs into structured data
    matching DevTrace's CodeChangeItem schema.

Responsibilities:
    - Parse git diff --numstat outputs (lines added, lines deleted).
    - Parse git diff --name-status outputs (added, modified, deleted, renamed).
    - Gracefully handle binary files, renames, and empty diffs.
    - Validate line counts and map status codes to DevTrace change types.
"""

from typing import Any


STATUS_MAP = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "added",     # Copied
    "T": "modified",  # Type changed (e.g., file to symlink)
}


def parse_name_status_line(line: str) -> tuple[str, str]:
    """
    Parse a single line from 'git diff-tree --name-status'.

    Format:
        'M\tsrc/auth.py'
        'A\ttests/test_auth.py'
        'R100\told_name.py\tnew_name.py'

    Returns:
        tuple[str, str]: (change_type, file_path)
    """
    parts = line.strip().split("\t")
    if not parts or not parts[0]:
        return "modified", ""

    raw_status = parts[0][0].upper()
    change_type = STATUS_MAP.get(raw_status, "modified")

    # If renamed (R100), the target/new file path is the last element
    file_path = parts[-1] if len(parts) > 1 else ""
    return change_type, file_path


def parse_numstat_output(numstat_text: str) -> dict[str, tuple[int | None, int | None]]:
    """
    Parse output from 'git diff-tree --numstat'.

    Format:
        '45\t10\tsrc/auth.py'
        '-\t-\tassets/logo.png'  (binary file)

    Returns:
        dict[str, tuple[int | None, int | None]]:
            Mapping of file_path -> (lines_added, lines_deleted)
    """
    stats: dict[str, tuple[int | None, int | None]] = {}

    for line in numstat_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        raw_added, raw_deleted = parts[0], parts[1]
        file_path = parts[-1]

        # Handle binary files where git outputs '-' instead of line numbers
        lines_added = int(raw_added) if raw_added.isdigit() else None
        lines_deleted = int(raw_deleted) if raw_deleted.isdigit() else None

        stats[file_path] = (lines_added, lines_deleted)

    return stats


def parse_git_diff_tree(
    name_status_text: str,
    numstat_text: str = "",
) -> list[dict[str, Any]]:
    """
    Combine --name-status and --numstat outputs into a list of CodeChangeItem dicts.

    Args:
        name_status_text: Output from 'git diff-tree -r --no-commit-id --name-status <commit>'
        numstat_text: Output from 'git diff-tree -r --no-commit-id --numstat <commit>'

    Returns:
        list[dict[str, Any]]: List of dictionary payloads matching CodeChangeItem schema.
    """
    numstats = parse_numstat_output(numstat_text) if numstat_text else {}
    changes: list[dict[str, Any]] = []

    for line in name_status_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        change_type, file_path = parse_name_status_line(line)
        if not file_path:
            continue

        lines_added, lines_deleted = numstats.get(file_path, (None, None))

        changes.append({
            "file_path": file_path,
            "change_type": change_type,
            "origin": "human",
            "confidence": 1.0,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "line_start": 1 if lines_added and lines_added > 0 else None,
            "line_end": lines_added if lines_added and lines_added > 0 else None,
        })

    return changes