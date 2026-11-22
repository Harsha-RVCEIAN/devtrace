"""
tests/integration/test_timeline.py

Integration tests for the unified chronological project timeline API.

Tests:
    1. Returns heterogeneous activity events (interactions, decisions, commits)
       sorted in descending chronological order.
    2. Enforces project membership (non-members receive 404).
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app
from app.models.entities import AIInteraction, Decision, GitCommit, Project, ProjectMember, User


def create_user_and_project(session):
    suffix = uuid4().hex[:8]
    user = User(name=f"Timeline User {suffix}", email=f"timeline_{suffix}@example.com")
    project = Project(project_name=f"Timeline Project {suffix}")
    session.add_all([user, project])
    session.flush()

    membership = ProjectMember(project_id=project.project_id, user_id=user.user_id, role="owner")
    session.add(membership)
    session.flush()
    return user, project


def test_project_timeline_returns_unified_sorted_feed(db_session):
    user, project = create_user_and_project(db_session)

    # 1. Add AI Interaction (earliest)
    t1 = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    interaction = AIInteraction(
        project_id=project.project_id,
        user_id=user.user_id,
        tool_name="ChatGPT",
        model_name="gpt-5",
        prompt="Should we use SQLite or PostgreSQL?",
        response="We chose PostgreSQL because of ACID compliance.",
        created_at=t1,
    )
    db_session.add(interaction)

    # 2. Add Decision (middle)
    t2 = datetime(2026, 7, 11, 14, 0, tzinfo=timezone.utc)
    decision = Decision(
        project_id=project.project_id,
        interaction_id=interaction.interaction_id,
        title="Adopt PostgreSQL",
        description="Relational database for ACID transactions",
        decision_type="architecture",
        status="active",
        reason_text="ACID compliance",
        reason_source_type="EXPLICIT",
        decided_at=t2,
    )
    db_session.add(decision)

    # 3. Add Git Commit (latest)
    t3 = datetime(2026, 7, 12, 16, 30, tzinfo=timezone.utc)
    commit = GitCommit(
        project_id=project.project_id,
        user_id=user.user_id,
        commit_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4",
        message="feat: setup PostgreSQL migrations",
        commit_time=t3,
    )
    db_session.add(commit)
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    response = client.get(
        f"/projects/{project.project_id}/timeline",
        headers={"X-User-ID": str(user.user_id)},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 3

    # Verify descending chronological order: Commit (t3) -> Decision (t2) -> Interaction (t1)
    assert events[0]["event_type"] == "commit"
    assert events[1]["event_type"] == "decision"
    assert events[2]["event_type"] == "interaction"


def test_project_timeline_rejects_non_members(db_session):
    user, project = create_user_and_project(db_session)
    outsider = User(name="Outsider", email=f"outsider_{uuid4().hex[:6]}@example.com")
    db_session.add(outsider)
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    response = client.get(
        f"/projects/{project.project_id}/timeline",
        headers={"X-User-ID": str(outsider.user_id)},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 404
