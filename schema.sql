
/*
Purpose:
    Document the complete DevTrace PostgreSQL schema.

Input:
    PostgreSQL database with UUID support (built into PostgreSQL).

Output:
    Nine relational tables with keys, constraints, and integrity rules.

Responsibilities:
    - Define tables in dependency order.
    - Enforce entity and referential integrity.
    - Validate statuses, provenance types, confidence, and line counts.
    - Prevent cross-project code-change references.
    - Preserve provenance history through RESTRICT deletion rules.

Important:
    This script creates a fresh schema. Run only against a disposable,
    empty development database. Use Alembic for normal schema upgrades.
*/

BEGIN;

-- Users
CREATE TABLE app_user (
    user_id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(320) NOT NULL UNIQUE,
    role VARCHAR(30) NOT NULL DEFAULT 'developer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Projects
CREATE TABLE project (
    project_id UUID PRIMARY KEY,
    project_name VARCHAR(200) NOT NULL,
    description TEXT,
    repository_url VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Membership: one user can belong to multiple projects.
CREATE TABLE project_member (
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'developer',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT project_member_pkey
        PRIMARY KEY (project_id, user_id),

    CONSTRAINT project_member_project_id_fkey
        FOREIGN KEY (project_id)
        REFERENCES project(project_id)
        ON DELETE RESTRICT,

    CONSTRAINT project_member_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES app_user(user_id)
        ON DELETE RESTRICT
);

-- AI interactions must belong to an actual project member.
CREATE TABLE ai_interaction (
    interaction_id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(150),
    external_session_ref VARCHAR(500),
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ai_interaction_project_id_user_id_fkey
        FOREIGN KEY (project_id, user_id)
        REFERENCES project_member(project_id, user_id)
        ON DELETE RESTRICT,

    CONSTRAINT ai_interaction_project_id_interaction_id_key
        UNIQUE (project_id, interaction_id)
);

-- Decisions can originate from an AI interaction or be recorded manually.
CREATE TABLE decision (
    decision_id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    interaction_id UUID,
    replaced_by_decision_id UUID,
    title VARCHAR(250) NOT NULL,
    description TEXT NOT NULL,
    decision_type VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'proposed',
    reason_text TEXT,
    reason_source_type VARCHAR(10) NOT NULL DEFAULT 'UNKNOWN',
    reason_confidence FLOAT,
    decided_at TIMESTAMPTZ,

    CONSTRAINT decision_project_id_fkey
        FOREIGN KEY (project_id)
        REFERENCES project(project_id)
        ON DELETE RESTRICT,

    CONSTRAINT decision_project_id_interaction_id_fkey
        FOREIGN KEY (project_id, interaction_id)
        REFERENCES ai_interaction(project_id, interaction_id)
        ON DELETE RESTRICT,

    CONSTRAINT decision_replaced_by_decision_id_fkey
        FOREIGN KEY (replaced_by_decision_id)
        REFERENCES decision(decision_id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_decision_status
        CHECK (status IN ('proposed', 'active', 'replaced', 'rejected')),

    CONSTRAINT ck_decision_reason_source
        CHECK (reason_source_type IN ('EXPLICIT', 'INFERRED', 'UNKNOWN')),

    CONSTRAINT ck_decision_reason_confidence
        CHECK (
            reason_confidence IS NULL
            OR (reason_confidence >= 0 AND reason_confidence <= 1)
        ),

    CONSTRAINT uq_decision_project_decision
        UNIQUE (project_id, decision_id)
);

-- Alternative options considered for a decision.
CREATE TABLE alternative (
    alternative_id UUID PRIMARY KEY,
    decision_id UUID NOT NULL,
    description TEXT NOT NULL,
    selection_status VARCHAR(20) NOT NULL DEFAULT 'considered',

    CONSTRAINT alternative_decision_id_fkey
        FOREIGN KEY (decision_id)
        REFERENCES decision(decision_id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_alternative_selection_status
        CHECK (selection_status IN ('selected', 'rejected', 'considered'))
);

-- Evidence supporting a decision.
CREATE TABLE evidence (
    evidence_id UUID PRIMARY KEY,
    decision_id UUID NOT NULL,
    evidence_type VARCHAR(80) NOT NULL,
    source_reference VARCHAR(2000) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT evidence_decision_id_fkey
        FOREIGN KEY (decision_id)
        REFERENCES decision(decision_id)
        ON DELETE RESTRICT
);

-- Git commits must belong to a project member.
CREATE TABLE git_commit (
    commit_id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    commit_hash VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    commit_time TIMESTAMPTZ NOT NULL,

    CONSTRAINT git_commit_project_id_user_id_fkey
        FOREIGN KEY (project_id, user_id)
        REFERENCES project_member(project_id, user_id)
        ON DELETE RESTRICT,

    CONSTRAINT git_commit_project_id_commit_hash_key
        UNIQUE (project_id, commit_hash),

    CONSTRAINT uq_git_commit_project_commit
        UNIQUE (project_id, commit_id)
);

-- Individual changes may have incomplete provenance.
-- Composite foreign keys prevent references across projects.
CREATE TABLE code_change (
    change_id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    commit_id UUID,
    interaction_id UUID,
    decision_id UUID,
    file_path VARCHAR(1000) NOT NULL,
    change_type VARCHAR(30) NOT NULL,
    origin VARCHAR(20) NOT NULL,
    confidence FLOAT,
    lines_added BIGINT,
    lines_deleted BIGINT,
    line_start BIGINT,
    line_end BIGINT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT code_change_project_id_fkey
        FOREIGN KEY (project_id)
        REFERENCES project(project_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_code_change_project_commit
        FOREIGN KEY (project_id, commit_id)
        REFERENCES git_commit(project_id, commit_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_code_change_project_interaction
        FOREIGN KEY (project_id, interaction_id)
        REFERENCES ai_interaction(project_id, interaction_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_code_change_project_decision
        FOREIGN KEY (project_id, decision_id)
        REFERENCES decision(project_id, decision_id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_code_change_origin
        CHECK (origin IN ('ai_exact', 'ai_inferred', 'human')),

    CONSTRAINT ck_code_change_confidence
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),

    CONSTRAINT ck_code_change_lines_added
        CHECK (lines_added IS NULL OR lines_added >= 0),

    CONSTRAINT ck_code_change_lines_deleted
        CHECK (lines_deleted IS NULL OR lines_deleted >= 0),

    CONSTRAINT ck_code_change_line_start
        CHECK (line_start IS NULL OR line_start >= 1),

    CONSTRAINT ck_code_change_line_end
        CHECK (line_end IS NULL OR line_end >= 1)
);

COMMIT;
