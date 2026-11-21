"""
tests/integration/test_commits.py

Integration tests for Git commit and code-change ingestion.

Tests:
    1. Atomic commit and changeset ingestion (happy path).
    2. Duplicate commit hash rejection for the same project.
    3. Cross-project provenance link rejection.
    4. HTTP API ingestion via POST /commits and retrieval via GET /commits/{id}.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_db
from app.main import app
from app.models.entities import AIInteraction, CodeChange, GitCommit, Project, ProjectMember, User
from app.schemas.commit import CodeChangeItem, CommitCreate
from app.services.commit_service import (
    get_commit,
    ingest_commit_with_changes,
    list_project_commits,
)


def create_user_and_project(session):
    """Helper to create and return an active user, project, and membership."""
    suffix = uuid4().hex[:8]
    user = User(
        name=f"Commit Author {suffix}",
        email=f"author_{suffix}@example.com",
    )
    project = Project(
        project_name=f"Commit Project {suffix}",
        description="Testing commit ingestion",
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


def test_ingest_commit_with_changes_success(db_session):
    """Verify that a commit and its changeset are persisted together."""
    user, project = create_user_and_project(db_session)

    payload = CommitCreate(
        project_id=project.project_id,
        commit_hash="a1b2c3d4e5f67890123456789abcdef012345678",
        message="feat: implement authentication module",
        commit_time=datetime.now(timezone.utc),
        changes=[
            CodeChangeItem(
                file_path="src/auth.py",
                change_type="added",
                origin="human",
                lines_added=45,
                lines_deleted=0,
                line_start=1,
                line_end=45,
            ),
            CodeChangeItem(
                file_path="tests/test_auth.py",
                change_type="added",
                origin="human",
                lines_added=30,
                lines_deleted=0,
            ),
        ],
    )

    commit = ingest_commit_with_changes(
        db=db_session,
        commit_data=payload,
        user_id=user.user_id,
    )

    assert commit.commit_id is not None
    assert commit.commit_hash == payload.commit_hash
    assert len(commit.changes) == 2

    # Query the database directly to confirm persistence
    saved_changes = list(
        db_session.scalars(
            select(CodeChange)
            .where(CodeChange.commit_id == commit.commit_id)
            .order_by(CodeChange.file_path.asc())
        ).all()
    )
    assert len(saved_changes) == 2
    assert saved_changes[0].file_path == "src/auth.py"
    assert saved_changes[0].lines_added == 45
    assert saved_changes[1].file_path == "tests/test_auth.py"


def test_duplicate_commit_hash_rejected(db_session):
    """Verify that PostgreSQL rejects duplicate commit hashes in the same project."""
    user, project = create_user_and_project(db_session)
    commit_hash = "abcdef0123456789abcdef0123456789abcdef01"

    payload1 = CommitCreate(
        project_id=project.project_id,
        commit_hash=commit_hash,
        message="Initial commit",
        commit_time=datetime.now(timezone.utc),
    )
    ingest_commit_with_changes(db_session, payload1, user.user_id)

    # Attempt to ingest the same commit hash again for the same project
    payload2 = CommitCreate(
        project_id=project.project_id,
        commit_hash=commit_hash,
        message="Duplicate attempt",
        commit_time=datetime.now(timezone.utc),
    )

    with pytest.raises(IntegrityError):
        ingest_commit_with_changes(db_session, payload2, user.user_id)


def test_cross_project_interaction_link_rejected(db_session):
    """Verify that attaching a change to an interaction from another project is rejected."""
    user_a, project_a = create_user_and_project(db_session)
    user_b, project_b = create_user_and_project(db_session)

    # Create interaction in Project B
    interaction_b = AIInteraction(
        project_id=project_b.project_id,
        user_id=user_b.user_id,
        tool_name="Claude",
        model_name="opus",
        prompt="Design auth",
        response="Use JWT",
    )
    db_session.add(interaction_b)
    db_session.flush()

    # Attempt to commit in Project A linking to Project B's interaction
    payload = CommitCreate(
        project_id=project_a.project_id,
        commit_hash="deadbeef1234567890abcdef1234567890abcdef",
        message="Attempt cross-project link",
        commit_time=datetime.now(timezone.utc),
        changes=[
            CodeChangeItem(
                file_path="src/jwt.py",
                change_type="added",
                origin="ai_inferred",
                confidence=0.85,
                interaction_id=interaction_b.interaction_id,  # From Project B!
            )
        ],
    )

    with pytest.raises(ValueError, match="Referenced AI interaction does not exist in this project"):
        ingest_commit_with_changes(db_session, payload, user_a.user_id)


def test_api_commit_endpoints(db_session):
    """Test HTTP POST /commits and GET /commits/{id} using TestClient."""
    user, project = create_user_and_project(db_session)

    # Override the FastAPI get_db dependency to use the active test session
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    try:
        # POST /commits with development auth header X-User-ID
        headers = {"X-User-ID": str(user.user_id)}
        response = client.post(
            "/commits",
            headers=headers,
            json={
                "project_id": str(project.project_id),
                "commit_hash": "11223344556677889900aabbccddeeff11223344",
                "message": "docs: add API documentation",
                "commit_time": datetime.now(timezone.utc).isoformat(),
                "changes": [
                    {
                        "file_path": "README.md",
                        "change_type": "modified",
                        "origin": "human",
                        "lines_added": 12,
                        "lines_deleted": 2,
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        commit_id = data["commit_id"]
        assert data["commit_hash"] == "11223344556677889900aabbccddeeff11223344"
        assert len(data["changes"]) == 1

        # GET /commits/{commit_id}
        get_response = client.get(f"/commits/{commit_id}", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["commit_id"] == commit_id
        assert get_data["changes"][0]["file_path"] == "README.md"

        # GET /projects/{project_id}/commits
        list_response = client.get(
            f"/projects/{project.project_id}/commits",
            headers=headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) >= 1

    finally:
        app.dependency_overrides.clear()