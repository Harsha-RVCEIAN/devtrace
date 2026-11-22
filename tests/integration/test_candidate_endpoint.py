"""
tests/integration/test_candidate_endpoint.py

Integration tests for the NLP candidate decision extraction API endpoint:
    POST /interactions/{interaction_id}/extract-candidates

Tests:
    1. Extracts proposed candidate decision with alternatives and explicit rationale.
    2. Rejects unauthorized / non-member access (HTTP 404).
    3. Returns empty candidates list for non-decision conversation turns.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app
from app.models.entities import AIInteraction, Project, ProjectMember, User


def create_user_and_project(session):
    suffix = uuid4().hex[:8]
    user = User(name=f"Candidate User {suffix}", email=f"candidate_{suffix}@example.com")
    project = Project(project_name=f"Candidate Project {suffix}")
    session.add_all([user, project])
    session.flush()

    membership = ProjectMember(project_id=project.project_id, user_id=user.user_id, role="owner")
    session.add(membership)
    session.flush()
    return user, project


def test_extract_candidates_from_interaction_success(db_session):
    user, project = create_user_and_project(db_session)

    interaction = AIInteraction(
        project_id=project.project_id,
        user_id=user.user_id,
        tool_name="ChatGPT",
        model_name="gpt-5",
        prompt="Should we use MongoDB or PostgreSQL for DevTrace?",
        response=(
            "We decided on PostgreSQL instead of MongoDB because native composite "
            "foreign keys enforce cross-project isolation at the database level. "
            "We also considered MySQL."
        ),
    )
    db_session.add(interaction)
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    response = client.post(
        f"/interactions/{interaction.interaction_id}/extract-candidates",
        headers={"X-User-ID": str(user.user_id)},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["engine_used"] == "rules"
    assert len(data["candidates"]) >= 1

    candidate = data["candidates"][0]
    assert candidate["title"] == "Adopt PostgreSQL"
    assert candidate["decision_type"] == "architecture"
    assert candidate["status"] == "proposed"  # Strict invariant
    assert candidate["reason_source_type"] == "EXPLICIT"
    assert candidate["reason_confidence"] >= 0.85
    assert len(candidate["alternatives"]) >= 2


def test_extract_candidates_rejects_non_members(db_session):
    user, project = create_user_and_project(db_session)
    outsider = User(name="Outsider", email=f"outsider_{uuid4().hex[:6]}@example.com")
    db_session.add(outsider)

    interaction = AIInteraction(
        project_id=project.project_id,
        user_id=user.user_id,
        tool_name="Claude",
        model_name="claude-opus-5-5",
        prompt="Which auth approach?",
        response="We decided on Redis sessions instead of JWT.",
    )
    db_session.add(interaction)
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    response = client.post(
        f"/interactions/{interaction.interaction_id}/extract-candidates",
        headers={"X-User-ID": str(outsider.user_id)},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 404


def test_extract_candidates_empty_when_no_decision(db_session):
    user, project = create_user_and_project(db_session)
    interaction = AIInteraction(
        project_id=project.project_id,
        user_id=user.user_id,
        tool_name="ChatGPT",
        model_name="gpt-5",
        prompt="What is the syntax for a foreign key in SQL?",
        response="In SQL, you write: FOREIGN KEY (id) REFERENCES other_table(id).",
    )
    db_session.add(interaction)
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    response = client.post(
        f"/interactions/{interaction.interaction_id}/extract-candidates",
        headers={"X-User-ID": str(user.user_id)},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["candidates"] == []
