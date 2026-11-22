"""
tests/unit/test_extractors.py

Unit tests for NLP extraction and provenance classification.

Tests:
    1. Rationale extraction: EXPLICIT vs INFERRED vs UNKNOWN.
    2. Alternative extraction: selected, rejected, considered.
    3. Candidate decision extraction pipeline.
    4. Code provenance origin classification (preserved).
"""

import pytest

from nlp.alternative_extractor import extract_alternatives
from nlp.decision_extractor import extract_candidate_decision
from nlp.pipeline import extract_decisions
from nlp.provenance_classifier import (
    classify_provenance_origin,
    compute_code_similarity,
)
from nlp.rationale_extractor import extract_rationale


# ---------------------------------------------------------------------------
# 1. Rationale Extraction Tests
# ---------------------------------------------------------------------------
def test_rationale_explicit():
    """Verify that direct causal statements are classified as EXPLICIT."""
    text = (
        "We chose PostgreSQL instead of MongoDB because native composite "
        "foreign keys provide database-level isolation."
    )
    result = extract_rationale(text)

    assert result.source_type == "EXPLICIT"
    assert result.confidence >= 0.85
    assert result.reason_text is not None
    assert "because" in result.reason_text.lower()


def test_rationale_inferred():
    """Verify that suggestive statements are classified as INFERRED."""
    text = (
        "It might be better to use Redis for session caching to improve performance."
    )
    result = extract_rationale(text)

    assert result.source_type == "INFERRED"
    assert 0.5 <= result.confidence <= 0.8
    assert result.reason_text is not None


def test_rationale_unknown_when_absent():
    """Verify that text with no justification returns UNKNOWN without hallucinating."""
    text = "Can you show me how to write a Python list comprehension?"
    result = extract_rationale(text)

    assert result.source_type == "UNKNOWN"
    assert result.confidence == 0.0
    assert result.reason_text is None


# ---------------------------------------------------------------------------
# 2. Alternative Extraction Tests
# ---------------------------------------------------------------------------
def test_alternative_extraction():
    """Verify extraction of selected, rejected, and considered alternatives."""
    text = (
        "We chose PostgreSQL instead of MongoDB, and we also considered MySQL "
        "as a potential database."
    )
    alts = extract_alternatives(text)

    assert len(alts) >= 2
    status_map = {a.description.lower(): a.selection_status for a in alts}

    # 'MongoDB' was preceded by 'instead of' -> rejected
    assert any("mongodb" in desc and status == "rejected" for desc, status in status_map.items())

    # 'MySQL' was preceded by 'considered' -> considered
    assert any("mysql" in desc and status == "considered" for desc, status in status_map.items())


# ---------------------------------------------------------------------------
# 3. Decision Candidate Pipeline Tests
# ---------------------------------------------------------------------------
def test_candidate_decision_generation():
    """Verify end-to-end candidate decision generation with status='proposed'."""
    prompt = "Should we use MongoDB or PostgreSQL for DevTrace?"
    response = (
        "We decided on PostgreSQL because composite foreign keys enforce "
        "cross-project isolation at the database level. We rejected MongoDB."
    )

    candidate = extract_candidate_decision(prompt, response)

    assert candidate is not None
    assert candidate.status == "proposed"  # Must NEVER be auto-approved
    assert candidate.decision_type in ["architecture", "implementation"]
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.85
    assert len(candidate.alternatives) >= 1


def test_candidate_decision_none_when_no_choice():
    """Verify that simple queries with no architectural choice return None."""
    prompt = "What is the syntax for a foreign key in SQL?"
    response = "In SQL, you write: FOREIGN KEY (id) REFERENCES other_table(id)."

    candidate = extract_candidate_decision(prompt, response)
    assert candidate is None


# ---------------------------------------------------------------------------
# 4. Provenance Classification Tests (Preserved)
# ---------------------------------------------------------------------------
def test_provenance_classification_exact():
    """Verify editor telemetry guarantees ai_exact classification."""
    origin, conf = classify_provenance_origin(has_editor_telemetry=True)
    assert origin == "ai_exact"
    assert conf == 1.0


def test_provenance_classification_inferred():
    """Verify high code similarity results in ai_inferred with proportional confidence."""
    ai_snippet = (
        "def hash_password(pwd: str) -> str:\n"
        "    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()"
    )
    diff_content = (
        "+def hash_password(pwd: str) -> str:\n"
        "+    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()"
    )

    origin, conf = classify_provenance_origin(
        has_editor_telemetry=False,
        ai_snippet=ai_snippet,
        diff_content=diff_content,
    )

    assert origin == "ai_inferred"
    assert conf >= 0.8


def test_provenance_classification_human_default():
    """Verify code with no telemetry or similarity defaults to human."""
    origin, conf = classify_provenance_origin(
        has_editor_telemetry=False,
        ai_snippet="SELECT * FROM table;",
        diff_content="print('Hello world')",
    )

    assert origin == "human"
    assert conf == 1.0
