"""
nlp/provenance_classifier.py

Purpose:
    Classification of code-change attribution origin (ai_exact, ai_inferred, human)
    and confidence calculation based on evidence type and code overlap.

Attribution Rules:
    - ai_exact: Direct telemetry from editor/IDE confirming AI code insertion.
    - ai_inferred: Heuristic overlap between AI transcript snippet and Git diff.
    - human: Default human developer commit with no AI telemetry.

Core Invariant:
    Never label heuristic similarity as ai_exact.
"""

import difflib
from typing import Literal


AttributionOrigin = Literal["ai_exact", "ai_inferred", "human"]


def _clean_diff_line(line: str) -> str:
    """Strip leading git diff markers (+, -) and surrounding whitespace."""
    line = line.strip()
    if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
        line = line[1:].strip()
    return line


def compute_code_similarity(ai_snippet: str, diff_content: str) -> float:
    """
    Compute normalized similarity ratio between AI response text and Git diff lines.

    Uses SequenceMatcher on tokenized lines to determine lexical overlap.

    Returns:
        float: Similarity ratio between 0.0 and 1.0.
    """
    if not ai_snippet or not diff_content:
        return 0.0

    # Clean and split into normalized non-empty lines
    ai_lines = [line.strip() for line in ai_snippet.splitlines() if line.strip()]
    diff_lines = [
        _clean_diff_line(line)
        for line in diff_content.splitlines()
        if _clean_diff_line(line)
    ]

    if not ai_lines or not diff_lines:
        return 0.0

    matcher = difflib.SequenceMatcher(None, ai_lines, diff_lines)
    return round(matcher.ratio(), 3)


def classify_provenance_origin(
    has_editor_telemetry: bool = False,
    ai_snippet: str | None = None,
    diff_content: str | None = None,
    similarity_threshold: float = 0.4,
) -> tuple[AttributionOrigin, float]:
    """
    Classify the origin of a code change and determine confidence.

    Args:
        has_editor_telemetry: True only if an editor plugin directly recorded
            the code insertion event from the AI.
        ai_snippet: Optional code text recommended by the AI.
        diff_content: Optional code text committed to Git.
        similarity_threshold: Minimum overlap ratio to qualify as ai_inferred.

    Returns:
        tuple[AttributionOrigin, float]: (origin, confidence_score)
    """
    # 1. Direct Evidence: Editor telemetry guarantees exact attribution
    if has_editor_telemetry:
        return "ai_exact", 1.0

    # 2. Heuristic Evidence: Calculate overlap between AI response and Git diff
    if ai_snippet and diff_content:
        ratio = compute_code_similarity(ai_snippet, diff_content)
        if ratio >= similarity_threshold:
            # Scale confidence proportionally to similarity ratio
            confidence = min(0.95, max(0.5, ratio))
            return "ai_inferred", round(confidence, 2)

    # 3. Default: Human authored
    return "human", 1.0