"""
tests/integration/test_reports.py

Integration tests verifying that the analytical SQL reports, views,
and stored functions execute cleanly against PostgreSQL.
"""

from uuid import UUID

import pytest
from sqlalchemy import text


def test_views_exist_and_queryable(db_session):
    """Verify that both analytical views can be queried without error."""
    # 1. active_decisions view
    res = db_session.execute(text("SELECT * FROM active_decisions LIMIT 5;"))
    assert res is not None

    # 2. changes_missing_provenance view
    res = db_session.execute(text("SELECT * FROM changes_missing_provenance LIMIT 5;"))
    assert res is not None


def test_stored_function_provenance_summary(db_session):
    """Verify that get_project_provenance_summary executes cleanly."""
    dummy_pid = "d3b07384-d113-4c92-b0b2-320d9f4c3912"
    query = text(f"SELECT * FROM get_project_provenance_summary('{dummy_pid}'::uuid);")
    row = db_session.execute(query).mappings().one()

    assert "total_changes" in row
    assert "ai_exact_changes" in row
    assert "ai_inferred_changes" in row
    assert "human_changes" in row
    assert "missing_provenance" in row
    assert "uncommitted_changes" in row


def test_recursive_decision_lineage_query(db_session):
    """Verify that the recursive CTE query executes without syntax or recursion error."""
    cte = text("""
        WITH RECURSIVE decision_lineage AS (
            SELECT
                d.decision_id,
                d.title,
                d.status,
                d.replaced_by_decision_id,
                1 AS generation
            FROM decision d
            WHERE d.replaced_by_decision_id IS NOT NULL

            UNION ALL

            SELECT
                replacement.decision_id,
                replacement.title,
                replacement.status,
                replacement.replaced_by_decision_id,
                dl.generation + 1
            FROM decision replacement
            JOIN decision_lineage dl ON dl.replaced_by_decision_id = replacement.decision_id
        )
        SELECT * FROM decision_lineage;
    """)
    res = db_session.execute(cte).fetchall()
    assert res is not None
