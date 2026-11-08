"""enforce code change project integrity

Revision ID: 52308b66b24b
Revises: a98dc062f7a1

Purpose:
    Enforce project consistency for code-change provenance links.

Migration strategy:
    - Validate existing provenance links before changing the schema.
    - Add project_id as nullable and backfill it from linked records.
    - Stop if project ownership is ambiguous or conflicting.
    - Add named composite constraints and enforce NOT NULL.
    - Preserve existing records and support downgrade.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "52308b66b24b"
down_revision: Union[str, Sequence[str], None] = "a98dc062f7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column as nullable first so existing rows are not rejected.
    op.add_column(
        "code_change",
        sa.Column("project_id", sa.Uuid(), nullable=True),
    )

    # Validate before backfilling. Never guess provenance ownership.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM code_change c
            LEFT JOIN git_commit gc
                ON gc.commit_id = c.commit_id
            LEFT JOIN ai_interaction ai
                ON ai.interaction_id = c.interaction_id
            LEFT JOIN decision d
                ON d.decision_id = c.decision_id
            WHERE
                (gc.project_id IS NOT NULL
                 AND ai.project_id IS NOT NULL
                 AND gc.project_id <> ai.project_id)
                OR
                (gc.project_id IS NOT NULL
                 AND d.project_id IS NOT NULL
                 AND gc.project_id <> d.project_id)
                OR
                (ai.project_id IS NOT NULL
                 AND d.project_id IS NOT NULL
                 AND ai.project_id <> d.project_id)
        ) THEN
            RAISE EXCEPTION
                'Migration stopped: code_change has cross-project links';
        END IF;

        IF EXISTS (
            SELECT 1
            FROM code_change
            WHERE commit_id IS NULL
              AND interaction_id IS NULL
              AND decision_id IS NULL
        ) THEN
            RAISE EXCEPTION
                'Migration stopped: project_id cannot be inferred for '
                'code_change rows without provenance links';
        END IF;
    END $$;
    """)

    # Backfill from a linked record whose project is known.
    op.execute("""
    UPDATE code_change AS c
    SET project_id = COALESCE(
        (SELECT project_id FROM git_commit
         WHERE commit_id = c.commit_id),
        (SELECT project_id FROM ai_interaction
         WHERE interaction_id = c.interaction_id),
        (SELECT project_id FROM decision
         WHERE decision_id = c.decision_id)
    )
    WHERE c.project_id IS NULL;
    """)

    # Do not make the column required unless every row has an owner.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM code_change WHERE project_id IS NULL
        ) THEN
            RAISE EXCEPTION
                'Migration stopped: some code_change rows could not be '
                'assigned a project';
        END IF;
    END $$;
    """)

    # Remove old single-column links before replacing them.
    op.drop_constraint(
        "code_change_commit_id_fkey", "code_change",
        type_="foreignkey",
    )
    op.drop_constraint(
        "code_change_interaction_id_fkey", "code_change",
        type_="foreignkey",
    )
    op.drop_constraint(
        "code_change_decision_id_fkey", "code_change",
        type_="foreignkey",
    )

    # Create candidate composite targets before dependent foreign keys.
    op.create_unique_constraint(
        "uq_git_commit_project_commit",
        "git_commit",
        ["project_id", "commit_id"],
    )
    op.create_unique_constraint(
        "uq_decision_project_decision",
        "decision",
        ["project_id", "decision_id"],
    )

    op.alter_column(
        "code_change",
        "project_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_code_change_project",
        "code_change",
        "project",
        ["project_id"],
        ["project_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_code_change_project_commit",
        "code_change",
        "git_commit",
        ["project_id", "commit_id"],
        ["project_id", "commit_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_code_change_project_interaction",
        "code_change",
        "ai_interaction",
        ["project_id", "interaction_id"],
        ["project_id", "interaction_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_code_change_project_decision",
        "code_change",
        "decision",
        ["project_id", "decision_id"],
        ["project_id", "decision_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Remove dependent constraints first.
    op.drop_constraint(
        "fk_code_change_project_commit", "code_change",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_code_change_project_interaction", "code_change",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_code_change_project_decision", "code_change",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_code_change_project", "code_change",
        type_="foreignkey",
    )

    op.drop_constraint(
        "uq_git_commit_project_commit", "git_commit",
        type_="unique",
    )
    op.drop_constraint(
        "uq_decision_project_decision", "decision",
        type_="unique",
    )

    # Restore the original foreign keys.
    op.create_foreign_key(
        "code_change_commit_id_fkey",
        "code_change",
        "git_commit",
        ["commit_id"],
        ["commit_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "code_change_interaction_id_fkey",
        "code_change",
        "ai_interaction",
        ["interaction_id"],
        ["interaction_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "code_change_decision_id_fkey",
        "code_change",
        "decision",
        ["decision_id"],
        ["decision_id"],
        ondelete="RESTRICT",
    )

    op.drop_column("code_change", "project_id")
