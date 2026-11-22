"""
tests/unit/test_transcript_nlp.py

Purpose:
    Integration-level evaluation of NLP extractors against realistic,
    multi-paragraph AI interaction transcripts with markdown formatting,
    code blocks, trade-off discussions, and multi-turn option selection.
"""

import pytest

from nlp.decision_extractor import extract_candidate_decision
from nlp.provenance_classifier import classify_provenance_origin, compute_code_similarity


def test_real_transcript_database_architecture():
    """
    Evaluate a realistic multi-paragraph architectural consultation
    comparing PostgreSQL, MongoDB, and MySQL for CampusCart.
    """
    prompt = (
        "CampusCart has users, listings and orders that reference each other. "
        "Should we stay on MongoDB or move to a relational database? "
        "We want strict referential integrity across checkout orders."
    )

    response = (
        "### Database Architecture Recommendation\n\n"
        "For an e-commerce platform like CampusCart with interconnected entities:\n\n"
        "1. **Recommendation:**\n"
        "   We decided on PostgreSQL instead of MongoDB because native composite "
        "foreign keys and ACID transactions guarantee cross-table referential integrity.\n\n"
        "2. **Alternative Options:**\n"
        "   - We also considered MySQL as a potential relational database, but "
        "PostgreSQL offers superior JSONB indexing for listing attributes.\n"
        "   - MongoDB was ruled out because eventual consistency risks orphaned records.\n\n"
        "### Next Steps:\n"
        "Run `alembic init` to create the initial migration."
    )

    candidate = extract_candidate_decision(prompt, response)

    assert candidate is not None
    assert candidate.status == "proposed"
    assert candidate.decision_type == "architecture"
    assert "PostgreSQL" in candidate.title
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.90
    assert "because" in candidate.reason_text.lower()

    # Verify extracted alternatives
    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert any("mongodb" in desc and status == "rejected" for desc, status in alt_map.items())
    assert any("mysql" in desc and status == "considered" for desc, status in alt_map.items())
    assert any("postgresql" in desc and status == "selected" for desc, status in alt_map.items())


def test_real_transcript_options_in_previous_para_selection():
    """
    Evaluate scenario where AI lists candidate options in an earlier paragraph
    and developer simply selects one with causal rationale without repeating
    the rejected options in the same sentence:
    'ok let's use sqlite since it's a simple db'
    """
    prompt = (
        "We previously evaluated several database options:\n"
        "- PostgreSQL\n"
        "- MySQL\n"
        "- SQLite\n"
        "- MongoDB\n\n"
        "ok let's use sqlite since it's a simple db"
    )

    response = "Understood. Configuring SQLite as the embedded relational engine."

    candidate = extract_candidate_decision(prompt, response)

    assert candidate is not None
    assert candidate.status == "proposed"
    assert candidate.decision_type == "architecture"
    assert "SQLite" in candidate.title
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.90
    assert "since" in candidate.reason_text.lower()

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    # SQLite was chosen
    assert any("sqlite" in desc and status == "selected" for desc, status in alt_map.items())
    # Other candidates from the pool were rejected
    assert any("postgresql" in desc and status == "rejected" for desc, status in alt_map.items())
    assert any("mysql" in desc and status == "rejected" for desc, status in alt_map.items())
    assert any("mongodb" in desc and status == "rejected" for desc, status in alt_map.items())


def test_real_transcript_auth_security_redesign():
    """
    Evaluate a security redesign transcript replacing stateless JWT
    with Redis-backed server sessions to support instant logout revocation.
    """
    prompt = (
        "Replace JWT auth with server-side sessions stored in Redis. "
        "We need to revoke sessions immediately on user logout."
    )

    response = (
        "### Authentication Redesign\n\n"
        "We chose Redis-backed server sessions rather than JWT in order to "
        "revoke active sessions immediately on logout.\n\n"
        "**Implementation Details:**\n"
        "- Session cookie stores encrypted session ID.\n"
        "- Redis key expires in 24 hours.\n"
    )

    candidate = extract_candidate_decision(prompt, response)

    assert candidate is not None
    assert candidate.status == "proposed"
    assert candidate.decision_type == "security"
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.90

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert any("jwt" in desc and status == "rejected" for desc, status in alt_map.items())
    assert any("redis" in desc and status == "selected" for desc, status in alt_map.items())


def test_real_transcript_debugging_negative_control():
    """
    Negative control: Verify that standard bug fixing or syntax questions
    do NOT trigger false positive candidate decisions.
    """
    prompt = (
        "I am getting 'TypeError: Cannot read properties of undefined (reading map)' "
        "in my React listing component. How do I fix this?"
    )

    response = (
        "This error happens when the listings array hasn't loaded from the API yet.\n\n"
        "Fix it using optional chaining:\n"
        "```tsx\n"
        "return (\n"
        "  <ul>\n"
        "    {items?.map(item => <li key={item.id}>{item.title}</li>)}\n"
        "  </ul>\n"
        ");\n"
        "```"
    )

    candidate = extract_candidate_decision(prompt, response)
    # Must be None — no engineering architecture decision was made!
    assert candidate is None


def test_real_transcript_code_provenance_diff_matching():
    """
    Evaluate provenance matching between a markdown-formatted AI code block
    and an actual Git diff patch.
    """
    ai_response = (
        "Here is the token extraction dependency for FastAPI:\n\n"
        "```python\n"
        "def get_current_user(token: str) -> User:\n"
        "    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])\n"
        "    return db.query(User).filter(User.id == payload.get('sub')).first()\n"
        "```\n\n"
        "Make sure to set SECRET_KEY in your environment."
    )

    git_diff = (
        "+def get_current_user(token: str) -> User:\n"
        "+    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])\n"
        "+    return db.query(User).filter(User.id == payload.get('sub')).first()"
    )

    origin, confidence = classify_provenance_origin(
        has_editor_telemetry=False,
        ai_snippet=ai_response,
        diff_content=git_diff,
    )

    assert origin == "ai_inferred"
    assert confidence >= 0.85
