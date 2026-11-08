"""
database_objects.py

Purpose:
    Define PostgreSQL objects managed by Alembic autogeneration.

Responsibilities:
    - Register provenance reporting views.
    - Register the project provenance summary function.
"""

from alembic_utils.pg_view import PGView
from alembic_utils.pg_function import PGFunction


active_decisions = PGView(
    schema="public",
    signature="active_decisions",
    definition="""
        SELECT
            decision_id,
            project_id,
            title,
            decision_type,
            decided_at
        FROM decision
        WHERE status = 'active'
    """,
)

changes_missing_provenance = PGView(
    schema="public",
    signature="changes_missing_provenance",
    definition="""
        SELECT
            change_id,
            project_id,
            file_path,
            origin,
            changed_at
        FROM code_change
        WHERE interaction_id IS NULL
          AND decision_id IS NULL
    """,
)

get_project_provenance_summary = PGFunction(
    schema="public",
    signature="get_project_provenance_summary(p_project_id uuid)",
    definition="""
        RETURNS TABLE (
            total_changes bigint,
            ai_exact_changes bigint,
            ai_inferred_changes bigint,
            human_changes bigint,
            missing_provenance bigint,
            uncommitted_changes bigint
        )
        LANGUAGE sql
        STABLE
        AS $$
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE origin = 'ai_exact'),
                COUNT(*) FILTER (WHERE origin = 'ai_inferred'),
                COUNT(*) FILTER (WHERE origin = 'human'),
                COUNT(*) FILTER (
                    WHERE interaction_id IS NULL
                       OR decision_id IS NULL
                ),
                COUNT(*) FILTER (WHERE commit_id IS NULL)
            FROM code_change
            WHERE project_id = p_project_id
        $$
    """,
)

database_objects = [
    active_decisions,
    changes_missing_provenance,
    get_project_provenance_summary,
]