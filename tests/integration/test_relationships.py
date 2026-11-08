
"""Integration tests for relational integrity."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.entities import CodeChange, GitCommit, Project, ProjectMember, User


def create_user(session):
    suffix = uuid4().hex[:12]
    user = User(
        name=f"Relationship Test User {suffix}",
        email=f"{suffix}@example.test",
    )
    session.add(user)
    session.flush()
    return user


def create_project(session):
    project = Project(project_name=f"Relationship Project {uuid4().hex[:8]}")
    session.add(project)
    session.flush()
    return project


def add_member(session, project, user):
    session.add(
        ProjectMember(
            project_id=project.project_id,
            user_id=user.user_id,
            role="member",
        )
    )
    session.flush()


def test_commit_from_another_project_is_rejected(db_session):
    user_a = create_user(db_session)
    user_b = create_user(db_session)

    project_a = create_project(db_session)
    project_b = create_project(db_session)

    add_member(db_session, project_a, user_a)
    add_member(db_session, project_b, user_b)

    commit_b = GitCommit(
        project_id=project_b.project_id,
        user_id=user_b.user_id,
        commit_hash="b" * 40,
        message="Commit in project B",
        commit_time=datetime.now(timezone.utc),
    )
    db_session.add(commit_b)
    db_session.flush()

    change = CodeChange(
        project_id=project_a.project_id,
        commit_id=commit_b.commit_id,
        file_path="src/example.py",
        change_type="modified",
        origin="human",
        confidence=1.0,
    )
    db_session.add(change)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_code_change_can_have_unknown_provenance(db_session):
    project = create_project(db_session)

    change = CodeChange(
        project_id=project.project_id,
        file_path="src/unlinked.py",
        change_type="added",
        origin="human",
        confidence=1.0,
    )
    db_session.add(change)
    db_session.flush()

    assert change.project_id == project.project_id
    assert change.commit_id is None
    assert change.interaction_id is None
    assert change.decision_id is None
