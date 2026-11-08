
"""Integration tests for AI interaction, decision, and code-change links."""

from uuid import uuid4

from sqlalchemy import select

from app.models.entities import (
    AIInteraction,
    CodeChange,
    Decision,
    Project,
    ProjectMember,
    User,
)


def test_code_change_links_to_interaction_and_decision(db_session):
    suffix = uuid4().hex[:12]

    user = User(
        name=f"Provenance Test User {suffix}",
        email=f"{suffix}@example.test",
    )
    project = Project(project_name=f"Provenance Project {suffix}")

    db_session.add_all([user, project])
    db_session.flush()

    db_session.add(
        ProjectMember(
            project_id=project.project_id,
            user_id=user.user_id,
            role="member",
        )
    )
    db_session.flush()

    interaction = AIInteraction(
        project_id=project.project_id,
        user_id=user.user_id,
        tool_name="OpenAI",
        model_name="test-model",
        prompt="Add a validation helper",
        response="Suggested a validation helper",
    )
    db_session.add(interaction)
    db_session.flush()

    decision = Decision(
        project_id=project.project_id,
        interaction_id=interaction.interaction_id,
        title="Keep validation in a dedicated helper",
        description="The helper keeps validation reusable.",
        decision_type="implementation",
        status="active",
        reason_source_type="EXPLICIT",
        reason_confidence=1.0,
        reason_text="The helper keeps validation reusable.",
    )
    db_session.add(decision)
    db_session.flush()

    change = CodeChange(
        project_id=project.project_id,
        interaction_id=interaction.interaction_id,
        decision_id=decision.decision_id,
        file_path="app/validation.py",
        change_type="added",
        origin="ai_inferred",
        confidence=0.75,
    )
    db_session.add(change)
    db_session.flush()

    result = db_session.execute(
        select(CodeChange, AIInteraction, Decision)
        .join(
            AIInteraction,
            CodeChange.interaction_id == AIInteraction.interaction_id,
        )
        .join(
            Decision,
            CodeChange.decision_id == Decision.decision_id,
        )
        .where(CodeChange.change_id == change.change_id)
    ).one()

    linked_change, linked_interaction, linked_decision = result

    assert linked_change.change_id == change.change_id
    assert linked_interaction.interaction_id == interaction.interaction_id
    assert linked_decision.decision_id == decision.decision_id
    assert linked_decision.interaction_id == interaction.interaction_id
