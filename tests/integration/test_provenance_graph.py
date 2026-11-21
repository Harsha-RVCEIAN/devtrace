"""
tests/integration/test_provenance_graph.py

Integration tests for the full DevTrace provenance tracing graph.

Tests:
    1. Full graph traversal: CodeChange -> GitCommit -> AIInteraction -> Decision -> Alternatives/Evidence.
    2. Explicit null preservation on unattributed code changes.
    3. Patching an unlinked code change to link it to a decision.
    4. Filtering project changes by missing_provenance_only=true.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app
from app.models.entities import (
    AIInteraction,
    Alternative,
    CodeChange,
    Decision,
    Evidence,
    GitCommit,
    Project,
    ProjectMember,
    User,
)
from app.schemas.commit import CodeChangeItem, CommitCreate
from app.services.commit_service import ingest_commit_with_changes


def setup_project(session):
    """Helper to create and return user, project, and membership."""
    suffix = uuid4().hex[:8]
    user = User(
        name=f"Dev {suffix}",
        email=f"dev_{suffix}@example.com",
    )
    project = Project(
        project_name=f"Provenance Demo {suffix}",
        description="Demo project for provenance graph",
    )
    session.add_all([user, project])
    session.flush()

    membership = ProjectMember(
        project_id=project.project_id,
        user_id=user.user_id,
        role="developer",
    )
    session.add(membership)
    session.flush()
    return user, project


def test_full_provenance_graph_query(db_session):
    """Verify that a code change returns its entire linked provenance hierarchy."""
    user, project = setup_project(db_session)

    # 1. Create an AI interaction
    interaction = AIInteraction(
        project_id=project.project_id,
        user_id=user.user_id,
        tool_name="Claude 3.7 Sonnet",
        model_name="claude-3-7-sonnet",
        prompt="Design a PostgreSQL schema for provenance tracking",
        response="Use composite foreign keys on (project_id, user_id)",
    )
    db_session.add(interaction)
    db_session.flush()

    # 2. Create a Decision with an Alternative and Evidence
    decision = Decision(
        project_id=project.project_id,
        interaction_id=interaction.interaction_id,
        title="Use Composite Foreign Keys for Project Isolation",
        description="Enforces at the database level that entities cannot cross projects.",
        decision_type="architecture",
        status="active",
        reason_text="Composite FKs provide foolproof database-level isolation.",
        reason_source_type="EXPLICIT",
        reason_confidence=1.0,
        decided_at=datetime.now(timezone.utc),
    )
    db_session.add(decision)
    db_session.flush()

    alternative = Alternative(
        decision_id=decision.decision_id,
        description="Application-layer validation only without composite FKs",
        selection_status="rejected",
    )
    evidence = Evidence(
        decision_id=decision.decision_id,
        evidence_type="architecture_benchmark",
        source_reference="docs/database_schema.md#composite-keys",
    )
    db_session.add_all([alternative, evidence])
    db_session.flush()

    # 3. Ingest a commit with a code change linked to both interaction and decision
    commit_payload = CommitCreate(
        project_id=project.project_id,
        commit_hash="c0ffee112233445566778899aabbccddeeff0011",
        message="feat: add composite foreign keys to schema",
        commit_time=datetime.now(timezone.utc),
        changes=[
            CodeChangeItem(
                file_path="schema.sql",
                change_type="modified",
                origin="ai_inferred",
                confidence=0.95,
                lines_added=35,
                lines_deleted=10,
                interaction_id=interaction.interaction_id,
                decision_id=decision.decision_id,
            )
        ],
    )
    commit = ingest_commit_with_changes(db_session, commit_payload, user.user_id)
    change_id = commit.changes[0].change_id

    # 4. Query the provenance endpoint via TestClient
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    try:
        response = client.get(
            f"/changes/{change_id}/provenance",
            headers={"X-User-ID": str(user.user_id)},
        )
        assert response.status_code == 200
        data = response.json()

        # Assert code change attributes
        assert data["change_id"] == str(change_id)
        assert data["file_path"] == "schema.sql"
        assert data["origin"] == "ai_inferred"
        assert data["confidence"] == 0.95

        # Assert commit link
        assert data["commit"] is not None
        assert data["commit"]["commit_hash"] == "c0ffee112233445566778899aabbccddeeff0011"
        assert data["commit"]["message"] == "feat: add composite foreign keys to schema"

        # Assert AI interaction link
        assert data["interaction"] is not None
        assert data["interaction"]["tool_name"] == "Claude 3.7 Sonnet"
        assert "composite foreign keys" in data["interaction"]["response"]

        # Assert Decision link with nested alternatives and evidence
        assert data["decision"] is not None
        assert data["decision"]["title"] == "Use Composite Foreign Keys for Project Isolation"
        assert data["decision"]["reason_source_type"] == "EXPLICIT"
        assert len(data["decision"]["alternatives"]) == 1
        assert data["decision"]["alternatives"][0]["selection_status"] == "rejected"
        assert len(data["decision"]["evidence"]) == 1
        assert data["decision"]["evidence"][0]["evidence_type"] == "architecture_benchmark"

    finally:
        app.dependency_overrides.clear()


def test_unattributed_code_change_preserves_none(db_session):
    """Verify that an unattributed change explicitly returns None for commit, interaction, and decision."""
    user, project = setup_project(db_session)

    # Standalone change without commit, interaction, or decision
    unlinked_change = CodeChange(
        project_id=project.project_id,
        file_path="src/untracked.py",
        change_type="added",
        origin="human",
        confidence=1.0,
    )
    db_session.add(unlinked_change)
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    try:
        response = client.get(
            f"/changes/{unlinked_change.change_id}/provenance",
            headers={"X-User-ID": str(user.user_id)},
        )
        assert response.status_code == 200
        data = response.json()

        # Missing links must remain explicitly None
        assert data["commit"] is None
        assert data["interaction"] is None
        assert data["decision"] is None

    finally:
        app.dependency_overrides.clear()


def test_patch_and_filter_unattributed_changes(db_session):
    """Verify PATCH /changes/{id} links provenance and filtering works."""
    user, project = setup_project(db_session)

    # 1. Create an unlinked change
    change = CodeChange(
        project_id=project.project_id,
        file_path="legacy.py",
        change_type="modified",
        origin="human",
    )
    db_session.add(change)
    db_session.flush()

    # 2. Create a decision to link later
    decision = Decision(
        project_id=project.project_id,
        title="Refactor Legacy Module",
        description="Clean up old technical debt",
        decision_type="refactor",
        status="active",
        reason_source_type="EXPLICIT",
    )
    db_session.add(decision)
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    headers = {"X-User-ID": str(user.user_id)}

    try:
        # Check missing_provenance_only filter returns our unlinked change
        res = client.get(
            f"/projects/{project.project_id}/code-changes?missing_provenance_only=true",
            headers=headers,
        )
        assert res.status_code == 200
        assert any(c["change_id"] == str(change.change_id) for c in res.json())

        # Link the change to the decision via PATCH
        patch_res = client.patch(
            f"/changes/{change.change_id}",
            headers=headers,
            json={
                "decision_id": str(decision.decision_id),
                "origin": "ai_exact",
                "confidence": 1.0,
            },
        )
        assert patch_res.status_code == 200
        patched_data = patch_res.json()
        assert patched_data["decision"]["title"] == "Refactor Legacy Module"
        assert patched_data["origin"] == "ai_exact"

        # Now check that missing_provenance_only filter no longer returns it!
        res_after = client.get(
            f"/projects/{project.project_id}/code-changes?missing_provenance_only=true",
            headers=headers,
        )
        assert res_after.status_code == 200
        assert not any(c["change_id"] == str(change.change_id) for c in res_after.json())

    finally:
        app.dependency_overrides.clear()