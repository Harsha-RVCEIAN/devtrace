
"""
entities.py

Purpose:
    Define all nine relational entities in the DevTrace database.

Input:
    Shared SQLAlchemy Base metadata.

Output:
    Table definitions, keys, constraints, and relationships.

Responsibilities:
    - Store users, projects, and project membership.
    - Record AI interactions and engineering decisions.
    - Track alternatives and supporting evidence.
    - Store Git commits and code-change provenance.
    - Enforce valid values and referential integrity.
"""

from sqlalchemy import Index, desc, text
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Float,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "app_user"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="developer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Project(Base):
    __tablename__ = "project"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProjectMember(Base):
    __tablename__ = "project_member"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project.project_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="developer")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AIInteraction(Base):
    __tablename__ = "ai_interaction"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["project_member.project_id", "project_member.user_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("project_id", "interaction_id"),
    )

    interaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(150))
    external_session_ref: Mapped[str | None] = mapped_column(String(500))
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Decision(Base):
    __tablename__ = "decision"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "interaction_id"],
            ["ai_interaction.project_id", "ai_interaction.interaction_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('proposed', 'active', 'replaced', 'rejected')",
            name="ck_decision_status",
        ),
        CheckConstraint(
            "reason_source_type IN ('EXPLICIT', 'INFERRED', 'UNKNOWN')",
            name="ck_decision_reason_source",
        ),
        CheckConstraint(
            "reason_confidence IS NULL OR "
            "(reason_confidence >= 0 AND reason_confidence <= 1)",
            name="ck_decision_reason_confidence",
        ),
        UniqueConstraint("project_id", "decision_id",
            name="uq_decision_project_decision"
        ),
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project.project_id", ondelete="RESTRICT"), nullable=False
    )
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    replaced_by_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("decision.decision_id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    decision_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    reason_text: Mapped[str | None] = mapped_column(Text)
    reason_source_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="UNKNOWN"
    )
    reason_confidence: Mapped[float | None] = mapped_column(Float)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Alternative(Base):
    __tablename__ = "alternative"
    __table_args__ = (
        CheckConstraint(
            "selection_status IN ('selected', 'rejected', 'considered')",
            name="ck_alternative_selection_status",
        ),
    )

    alternative_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("decision.decision_id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    selection_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="considered"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("decision.decision_id", ondelete="RESTRICT"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(2000), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GitCommit(Base):
    __tablename__ = "git_commit"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["project_member.project_id", "project_member.user_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("project_id", "commit_hash"),
        UniqueConstraint(
            "project_id", "commit_id",
            name="uq_git_commit_project_commit",
        ),
    )

    commit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    commit_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CodeChange(Base):
    __tablename__ = "code_change"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "commit_id"],
            ["git_commit.project_id", "git_commit.commit_id"],
            name="fk_code_change_project_commit",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "interaction_id"],
            ["ai_interaction.project_id", "ai_interaction.interaction_id"],
            name="fk_code_change_project_interaction",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "decision_id"],
            ["decision.project_id", "decision.decision_id"],
            name="fk_code_change_project_decision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "origin IN ('ai_exact', 'ai_inferred', 'human')",
            name="ck_code_change_origin",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_code_change_confidence",
        ),
        CheckConstraint(
            "lines_added IS NULL OR lines_added >= 0",
            name="ck_code_change_lines_added",
        ),
        CheckConstraint(
            "lines_deleted IS NULL OR lines_deleted >= 0",
            name="ck_code_change_lines_deleted",
        ),
        CheckConstraint(
            "line_start IS NULL OR line_start >= 1",
            name="ck_code_change_line_start",
        ),
        CheckConstraint(
            "line_end IS NULL OR line_end >= 1",
            name="ck_code_change_line_end",
        ),
        Index(
            "idx_code_change_decision_id",
            "decision_id",
        ),
        Index(
            "idx_code_change_missing_provenance",
            "project_id",
            desc("changed_at"),
            postgresql_where=text(
                "interaction_id IS NULL AND decision_id IS NULL"
            ),
        ),
    )

    change_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("project.project_id", ondelete="RESTRICT"),
        nullable=False,
    )
    commit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    change_type: Mapped[str] = mapped_column(String(30), nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    lines_added: Mapped[int | None] = mapped_column(BigInteger)
    lines_deleted: Mapped[int | None] = mapped_column(BigInteger)
    line_start: Mapped[int | None] = mapped_column(BigInteger)
    line_end: Mapped[int | None] = mapped_column(BigInteger)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
