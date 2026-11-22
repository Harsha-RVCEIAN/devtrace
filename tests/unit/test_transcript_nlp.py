"""
tests/unit/test_transcript_nlp.py

Purpose:
    Integration-level evaluation of NLP extractors against realistic,
    multi-paragraph AI interaction transcripts with markdown formatting,
    code blocks, multi-turn dialogues, casual phrasing, and option selection.
"""

import pytest

from nlp.decision_extractor import extract_candidate_decision
from nlp.pipeline import extract_decisions
from nlp.provenance_classifier import classify_provenance_origin, compute_code_similarity


def test_user_acceptance_conversational_security_auth():
    """
    Acceptance Case 1 (The user's example):
    Developer asks a question listing options with 'or', expresses preference casually:
    'ok i feel like session based auth is the best here'
    Assistant responds affirmatively with implicit rationale:
    'Definitely! it has a simpler lifecycle and safer browser storage.'
    """
    prompt = (
        "how do we secure our website? JWT? or redis session based auth, or mutual TLS?\n"
        "ok i feel like session based auth is the best here"
    )
    response = (
        "Definitely! it has a simpler lifecycle and safer browser storage. "
        "creating the files now..."
    )

    result = extract_decisions([(prompt, response)], engine="rules")
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.status == "proposed"
    assert candidate.decision_type == "security"
    assert candidate.chosen_option == "Redis Session Based Auth"
    assert candidate.title == "Adopt Redis Session Based Auth"
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.80
    assert "simpler lifecycle" in (candidate.reason_text or "")

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert alt_map.get("redis session based auth") == "selected"
    assert alt_map.get("jwt") == "rejected"
    assert any("mutual tls" in k and s == "rejected" for k, s in alt_map.items())

    # Check evidence contains context question
    roles = [e.role for e in candidate.evidence]
    assert "context" in roles
    assert "decision" in roles
    assert "rationale" in roles


def test_multi_turn_dialogue_with_typo_fix():
    """
    Acceptance Case 2: Multi-turn dialogue where developer accepts recommendation
    and follows with a non-decision task (fixing a typo).
    """
    turns = [
        (
            "which database should we use, postgres or mongo? i was thinking mongo",
            "PostgreSQL is a better fit: it provides ACID compliance across orders.",
        ),
        (
            "fair, postgres it is. also fix the typo in the navbar",
            "Done, fixed the typo in the navbar component.",
        ),
    ]

    result = extract_decisions(turns, engine="rules")
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.chosen_option == "PostgreSQL"
    assert candidate.decision_type == "architecture"
    assert candidate.confidence >= 0.85
    assert candidate.reason_source_type == "EXPLICIT"
    assert "acid" in (candidate.reason_text or "").lower()

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert alt_map.get("postgresql") == "selected"
    assert alt_map.get("mongodb") == "rejected"


def test_real_transcript_bullet_options_selection():
    """
    Acceptance Case 3: Bullets preceding a causal selection.
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

    result = extract_decisions([(prompt, response)], engine="rules")
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.title == "Adopt SQLite"
    assert candidate.decision_type == "architecture"
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.90
    assert "since" in (candidate.reason_text or "").lower()

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert alt_map.get("sqlite") == "selected"
    assert alt_map.get("postgresql") == "rejected"
    assert alt_map.get("mysql") == "rejected"
    assert alt_map.get("mongodb") == "rejected"


def test_real_transcript_auth_security_redesign():
    """
    Acceptance Case 4: Security redesign replacing JWT with Redis sessions.
    """
    prompt = (
        "Replace JWT auth with server-side sessions stored in Redis. "
        "We need to revoke sessions immediately on user logout."
    )
    response = (
        "We chose Redis-backed server sessions rather than JWT in order to "
        "revoke active sessions immediately on logout."
    )

    result = extract_decisions([(prompt, response)], engine="rules")
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.decision_type == "security"
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.80

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert any("jwt" in k and s == "rejected" for k, s in alt_map.items())


def test_real_transcript_database_architecture():
    """
    Acceptance Case 5: Multi-paragraph architectural consultation
    comparing PostgreSQL, MongoDB, and MySQL.
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
        "   - MongoDB was ruled out because eventual consistency risks orphaned records."
    )

    result = extract_decisions([(prompt, response)], engine="rules")
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.decision_type == "architecture"
    assert "PostgreSQL" in candidate.title
    assert candidate.reason_source_type == "EXPLICIT"
    assert candidate.reason_confidence >= 0.90
    assert "because" in (candidate.reason_text or "").lower()

    alt_map = {a.description.lower(): a.selection_status for a in candidate.alternatives}
    assert any("mongodb" in desc and status == "rejected" for desc, status in alt_map.items())
    assert any("mysql" in desc and status == "considered" for desc, status in alt_map.items())
    assert any("postgresql" in desc and status == "selected" for desc, status in alt_map.items())


def test_seed_data_recommendation_extraction():
    """
    Acceptance Case 7: Direct tool recommendation from LibTrack seed data.
    """
    prompt = "Which barcode scanning library should we use for LibTrack mobile?"
    response = (
        "Use ZXing through react-native-vision-camera because it works offline "
        "and supports code 128 barcodes."
    )

    result = extract_decisions([(prompt, response)], engine="rules")
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert "ZXing" in candidate.title
    assert candidate.reason_source_type == "EXPLICIT"
    assert "offline" in (candidate.reason_text or "")


def test_real_transcript_debugging_negative_control():
    """
    Acceptance Case 6: Negative control: Syntax/debugging queries return 0 candidates.
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

    result = extract_decisions([(prompt, response)], engine="rules")
    assert len(result.candidates) == 0


def test_real_transcript_code_provenance_diff_matching():
    """
    Code provenance matching between AI code block and Git diff patch.
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
