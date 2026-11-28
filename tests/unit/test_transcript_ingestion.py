"""Unit tests for transcript parsing, drop-and-use NLP rule, and /interactions/ingest staging + auto-linking."""

from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.entities  # noqa: F401
from app.api.dependencies import get_db
from app.db.base import Base
from app.main import app
from integrations.ai.adapters.transcript_parser import parse_transcript
from nlp.pipeline import extract_decisions


def test_parse_chatgpt_export_json():
    export = {
        "id": "conv-123",
        "current_node": "n4",
        "mapping": {
            "n1": {"parent": None, "message": {"author": {"role": "system"}, "content": {"parts": ["sys"]}}},
            "n2": {"parent": "n1", "message": {"author": {"role": "user"}, "content": {"parts": ["Use Redis or JWT?"]}}},
            "n3": {"parent": "n2", "message": {"author": {"role": "assistant"}, "metadata": {"model_slug": "gpt-4o"}, "content": {"parts": ["Redis sessions are revocable."]}}},
            "n4": {"parent": "n3", "message": {"author": {"role": "user"}, "content": {"parts": ["Let's drop JWT and use Redis sessions because logout must revoke tokens."]}}},
        },
    }
    parsed = parse_transcript(json.dumps(export))
    assert parsed.tool_name == "ChatGPT"
    assert parsed.model_name == "gpt-4o"
    assert parsed.external_session_ref == "conv-123"
    assert len(parsed.turns) == 2
    assert parsed.turns[0][0] == "Use Redis or JWT?"


def test_parse_markdown_transcript():
    md = """
    User: Should we use PostgreSQL or MongoDB?
    Assistant: PostgreSQL gives ACID guarantees.
    Developer: Agreed, let's go with PostgreSQL.
    AI: Sounds good!
    """
    parsed = parse_transcript(md, tool_name="Claude")
    assert len(parsed.turns) == 2
    assert "PostgreSQL" in parsed.turns[1][0]


def test_drop_and_use_decision_extraction():
    res = extract_decisions(
        turns=[
            (
                "Should we use JWT or Redis server sessions?",
                "Redis server sessions are safer for logout.",
            ),
            (
                "Yeah true, let's drop JWT and use Redis server sessions instead because users must be logged out immediately.",
                "Done.",
            ),
        ],
        engine="rules",
    )
    assert len(res.candidates) == 1
    assert "Redis Server Sessions" in res.candidates[0].title
    rejected = [a.description for a in res.candidates[0].alternatives if a.selection_status == "rejected"]
    assert any("JWT" in r for r in rejected)


def test_ingest_transcript_endpoint_stages_proposed_and_autolinks():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        r = client.post(
            "/auth/register",
            json={"name": "Adithya", "email": "adi@example.com", "password": "password123"},
        )
        assert r.status_code == 201

        proj = client.post(
            "/projects",
            json={"project_name": "CampusCart", "description": "Test"},
        ).json()
        pid = proj["project_id"]

        client.post(
            "/commits",
            json={
                "project_id": pid,
                "commit_hash": "a" * 40,
                "message": "feat(auth): add session store",
                "commit_time": datetime.now(timezone.utc).isoformat(),
                "changes": [
                    {
                        "file_path": "app/auth/session_store.py",
                        "change_type": "added",
                        "origin": "human",
                        "lines_added": 50,
                        "lines_deleted": 0,
                    },
                    {
                        "file_path": "README.md",
                        "change_type": "modified",
                        "origin": "human",
                        "lines_added": 2,
                        "lines_deleted": 1,
                    },
                ],
            },
        )

        md_chat = (
            "User: In app/auth/session_store.py should we use JWT or Redis server sessions?\n"
            "Assistant: Redis server sessions support immediate logout revocation.\n"
            "User: Let's drop JWT and use Redis server sessions instead because logout must revoke immediately.\n"
            "Assistant: Implementing session_store.py now."
        )
        ingest = client.post(
            "/interactions/ingest",
            json={
                "project_id": pid,
                "tool_name": "ChatGPT",
                "engine": "rules",
                "raw_text": md_chat,
                "auto_link": True,
            },
        )
        assert ingest.status_code == 201, ingest.text
        data = ingest.json()
        assert data["turns_count"] == 2
        assert len(data["staged_decisions"]) == 1
        assert data["staged_decisions"][0]["status"] == "active"
        # Auto-linked only session_store.py (mentioned in chat), not README.md
        assert len(data["auto_linked_changes"]) == 1
        assert data["auto_linked_changes"][0]["file_path"] == "app/auth/session_store.py"
        assert data["auto_linked_changes"][0]["origin"] == "ai_inferred"

        # Batch multi-conversation Markdown separated by `---`
        batch = client.post(
            "/interactions/ingest-batch",
            json={
                "project_id": pid,
                "engine": "rules",
                "auto_approve": False,
                "raw_text": (
                    "User: Should we use PostgreSQL or MongoDB?\n"
                    "Assistant: PostgreSQL gives ACID transactions.\n"
                    "User: Let's go with PostgreSQL.\n"
                    "---\n"
                    "User: Why is uvicorn throwing address already in use?\n"
                    "Assistant: Another process is already listening on that port.\n"
                ),
            },
        )
        assert batch.status_code == 201, batch.text
        bdata = batch.json()
        assert bdata["interactions_count"] == 2
        assert len(bdata["staged_decisions"]) == 1
        assert bdata["staged_decisions"][0]["status"] == "proposed"
    finally:
        app.dependency_overrides.clear()
