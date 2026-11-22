"""
app/services/timeline_service.py

Purpose:
    Aggregate, normalize, and sort heterogeneous development activity
    (AI interactions, engineering decisions, Git commits) into a unified
    chronological activity timeline.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import AIInteraction, Decision, GitCommit
from app.schemas.project import TimelineEventResponse


def get_project_timeline(
    db: Session,
    project_id: UUID,
    limit: int = 100,
) -> list[TimelineEventResponse]:
    """
    Construct a unified chronological timeline for a project.

    Fetches:
      1. AI interactions (ordered by created_at)
      2. Engineering decisions (ordered by decided_at or fallback)
      3. Git commits (ordered by commit_time)

    Returns:
        list[TimelineEventResponse]: Combined events sorted chronologically (newest first).
    """
    events: list[TimelineEventResponse] = []

    # 1. Fetch AI interactions
    interactions = db.scalars(
        select(AIInteraction)
        .where(AIInteraction.project_id == project_id)
        .order_by(desc(AIInteraction.created_at))
        .limit(limit)
    ).all()

    for item in interactions:
        prompt_snippet = item.prompt.strip().split("\n")[0][:100]
        events.append(
            TimelineEventResponse(
                event_id=item.interaction_id,
                event_type="interaction",
                timestamp=item.created_at,
                title=f"AI Interaction ({item.tool_name})",
                actor_id=item.user_id,
                details={
                    "tool_name": item.tool_name,
                    "model_name": item.model_name,
                    "prompt_preview": prompt_snippet,
                    "external_session_ref": item.external_session_ref,
                },
            )
        )

    # 2. Fetch engineering decisions
    decisions = db.scalars(
        select(Decision)
        .where(Decision.project_id == project_id)
        .order_by(desc(Decision.decided_at))
        .limit(limit)
    ).all()

    for item in decisions:
        ts = item.decided_at or datetime.now(timezone.utc)
        events.append(
            TimelineEventResponse(
                event_id=item.decision_id,
                event_type="decision",
                timestamp=ts,
                title=f"Decision: {item.title}",
                actor_id=None,
                details={
                    "decision_type": item.decision_type,
                    "status": item.status,
                    "reason_source_type": item.reason_source_type,
                    "reason_text": item.reason_text,
                    "replaced_by_decision_id": str(item.replaced_by_decision_id)
                    if item.replaced_by_decision_id
                    else None,
                },
            )
        )

    # 3. Fetch Git commits
    commits = db.scalars(
        select(GitCommit)
        .where(GitCommit.project_id == project_id)
        .order_by(desc(GitCommit.commit_time))
        .limit(limit)
    ).all()

    for item in commits:
        message_subject = item.message.strip().split("\n")[0][:100]
        events.append(
            TimelineEventResponse(
                event_id=item.commit_id,
                event_type="commit",
                timestamp=item.commit_time,
                title=f"Commit: {message_subject}",
                actor_id=item.user_id,
                details={
                    "commit_hash": item.commit_hash,
                    "message": item.message,
                },
            )
        )

    # Sort all events chronologically descending (newest first)
    events.sort(key=lambda ev: ev.timestamp, reverse=True)
    return events[:limit]
