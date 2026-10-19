# Intelligent Software Development Provenance System

> An evidence-aware provenance layer for AI-assisted software
> development. It connects AI interactions, engineering decisions,
> alternatives, evidence, Git commits, and code changes so developers
> can understand what changed, why it changed, and what source supports
> that history.

## Overview

Software development context is often scattered across AI conversations,
source files, Git commits, technical notes, and developer decisions. Git
is effective at recording versions and commits, but it does not
necessarily preserve why a change was made or which AI interaction
influenced it. AI conversations may contain useful reasoning and
rejected approaches, but those details can become disconnected from the
resulting code.

The **Intelligent Software Development Provenance System** provides a
centralized, queryable record of this development history. PostgreSQL is
the system of record. NLP processes supported unstructured development
text and proposes structured decisions, rationale, and alternatives.
Extracted information is validated before becoming an approved record.

**Core principle:** record supported evidence, distinguish inference
from fact, and never invent a missing rationale.

## Problem Statement

AI-assisted software development creates a gap between a code change and
the context that led to it. A developer may see a changed file or commit
but not know which prompt, decision, or alternative was involved.
Manually maintained architecture decision records can help, but they may
not be consistently linked to actual code changes and commits.

This project connects: - AI prompts and responses; - engineering
decisions and recorded rationale; - considered alternatives and
supporting evidence; - Git commits; and - file-level or line-range
code-change metadata.

## Objectives

-   Maintain a centralized relational record of software-development
    provenance.
-   Link interactions, decisions, commits, and code changes where
    evidence supports the association.
-   Use NLP to extract candidate decisions, reasons, and alternatives.
-   Distinguish `EXPLICIT`, `INFERRED`, and `UNKNOWN` rationale.
-   Require human validation before extracted information becomes an
    approved decision.
-   Preserve rejected and replaced decision history.
-   Provide provenance reports and controlled history retrieval for
    authorized AI tools.
-   Demonstrate practical DBMS concepts: keys, constraints,
    normalization, joins, transactions, views, indexes, and routines
    where implemented.

## Novelty and Differentiation

This is **not primarily an AI-memory system**. AI-memory tools generally
focus on what context an assistant should retain for future work. This
project focuses on the historical provenance of engineering work: what
was recorded, how a decision evolved, and what evidence connects it to
code.

The system does not promise perfect attribution for every line. It
records the strength and source of an association and permits unknown
provenance when evidence is insufficient.

## Main Features

### Developer-facing

-   Trace a code change to its recorded commit, AI interaction,
    decision, and evidence.
-   View active, rejected, and replaced decisions.
-   Inspect rationale and its source classification.
-   Review alternatives and their selection status.
-   Identify changes without a recorded AI interaction or decision.
-   Produce project timelines, contributor reports, and AI-attribution
    summaries.
-   Compare activity by AI tool/model without treating activity counts
    as code-quality scores.
-   Prioritize review of AI-attributed code that has not subsequently
    been human-edited, when the required history is available.

### AI-facing

The intended controlled interface can expose operations such as: -
`why_does_this_exist(file, line)` - `get_active_decisions(project)` -
`get_rejected_alternatives(topic)` - `check_change(description)` -
`record_decision(...)` --- submit a candidate for developer approval,
not silently accept it.

These are intended operations; actual availability depends on the
implemented API/MCP integration.

## Architecture

``` text
Developer / AI Coding Assistant
              |
     Editor Hook / Adapter
              |
              v
       FastAPI Ingestion API <------ Git Collector / Hooks
              |                              |
              v                              v
      Validation + NLP                  Commit / Diff Data
              |
              v
      Human Review / Approval
              |
              v
          PostgreSQL
        (system of record)
              |
        +-----+------+
        |            |
   Dashboard    Controlled MCP
                Read Interface
```

### Component responsibilities

-   **Capture adapters:** gather supported AI interaction and
    development-event metadata.
-   **FastAPI:** validates requests, checks authorization, and
    coordinates database operations.
-   **NLP processor:** proposes candidate decisions, reasons,
    alternatives, and source references.
-   **Validation/review:** checks project context and allows a developer
    to approve, edit, or reject candidates.
-   **PostgreSQL:** stores normalized, authoritative provenance records.
-   **Git collector:** captures commit metadata and available diff
    information.
-   **Dashboard:** displays provenance and project history.
-   **MCP interface:** offers named, project-scoped operations to
    compatible AI clients.

The prototype should implement one clearly supported editor/AI-tool path
plus Git integration rather than claiming access to every AI platform.

## Workflow

1.  A user creates a project and adds project members.
2.  A supported adapter captures an AI interaction and sends it to the
    API.
3.  The backend validates the payload and verifies project membership.
4.  Git integration records commit metadata and available change
    information.
5.  NLP proposes candidate decisions, reasons, alternatives, and
    evidence references.
6.  A developer reviews and approves, edits, or rejects the candidate.
7.  Approved decisions and their alternatives/evidence are stored in
    PostgreSQL.
8.  Code changes are linked to commits, interactions, and decisions
    where evidence supports the association.
9.  The dashboard and authorized AI interface retrieve the recorded
    history.

Not every record must have every link. Missing links remain missing
rather than being guessed.

## Technology Stack

  -----------------------------------------------------------------------
  Layer                   Technology              Role
  ----------------------- ----------------------- -----------------------
  Frontend                React.js                Developer dashboard

  Backend                 Python + FastAPI        REST API and business
                                                  logic

  Database                PostgreSQL              Normalized system of
                                                  record

  NLP                     Python                  Candidate extraction
                          sentence-embedding      and semantic matching
                          model and               
                          text-processing         
                          utilities               

  Version control         Git                     Commit metadata and
                                                  available diffs

  AI integration          MCP                     Controlled access to
                                                  named provenance
                                                  operations

  Communication           REST/HTTP + JSON        Component communication

  Database access         PostgreSQL driver or    Parameterized
                          ORM                     operations and
                                                  transactions

  Development             VS Code + Git           Coding and version
                                                  control
  -----------------------------------------------------------------------

The exact library versions, NLP model, and deployment method should be
recorded once chosen in the repository. A local NLP model and rule-based
fallback are intended so the basic prototype need not depend on a paid
hosted model.

## Database Design

The logical schema has nine relations and is designed toward **Third
Normal Form (3NF)**. Independent entities are separated, many-to-many
membership is represented by an associative relation, and
alternatives/evidence are separate rows rather than comma-separated
fields.

### 1. USER

``` text
USER(
  user_id PK, name, email UNIQUE, role, created_at
)
```

Stores application users.

### 2. PROJECT

``` text
PROJECT(
  project_id PK, project_name, description, repository_url, created_at
)
```

Stores tracked projects.

### 3. PROJECT_MEMBER

``` text
PROJECT_MEMBER(
  project_id PK/FK -> PROJECT.project_id,
  user_id PK/FK -> USER.user_id,
  role, joined_at
)
```

Associates users with projects. `(project_id, user_id)` is the composite
primary key and prevents duplicate membership.

### 4. AI_INTERACTION

``` text
AI_INTERACTION(
  interaction_id PK,
  project_id, user_id,
  tool_name, model_name, external_session_ref,
  prompt, response, created_at,
  FK (project_id, user_id)
    -> PROJECT_MEMBER(project_id, user_id)
)
```

Stores captured AI interactions. The composite foreign key ensures the
user is a member of the referenced project.

### 5. DECISION

``` text
DECISION(
  decision_id PK,
  project_id FK -> PROJECT.project_id,
  interaction_id FK -> AI_INTERACTION.interaction_id NULL,
  replaced_by_decision_id FK -> DECISION.decision_id NULL,
  title, description, decision_type, status,
  reason_text, reason_source_type, reason_confidence, decided_at
)
```

Stores technical decisions. `interaction_id` may be null for a manually
recorded decision. `replaced_by_decision_id` is a self-referencing
foreign key that preserves replacement history.

Suggested `status` values: `proposed`, `active`, `replaced`, `rejected`.

Suggested `reason_source_type` values: - `EXPLICIT`: the source directly
states the reason. - `INFERRED`: the reason is inferred and must be
labelled as such. - `UNKNOWN`: no sufficiently supported reason is
available.

### 6. ALTERNATIVE

``` text
ALTERNATIVE(
  alternative_id PK,
  decision_id FK -> DECISION.decision_id,
  description, selection_status
)
```

Stores approaches considered for a decision.

### 7. EVIDENCE

``` text
EVIDENCE(
  evidence_id PK,
  decision_id FK -> DECISION.decision_id,
  evidence_type, source_reference, captured_at
)
```

Stores source references supporting a decision. The referenced content
may remain in its original system.

### 8. COMMIT

``` text
COMMIT(
  commit_id PK,
  project_id, user_id,
  commit_hash UNIQUE, message, commit_time,
  FK (project_id, user_id)
    -> PROJECT_MEMBER(project_id, user_id)
)
```

Stores Git commit metadata. The composite membership foreign key
verifies project membership. If commit hashes are only unique within a
repository in the actual implementation, use a repository/project-scoped
uniqueness constraint. `COMMIT` can conflict with SQL keyword usage;
consider naming the physical table `git_commit`, or quote the chosen
identifier consistently.

### 9. CODE_CHANGE

``` text
CODE_CHANGE(
  change_id PK,
  commit_id FK -> COMMIT.commit_id NULL,
  interaction_id FK -> AI_INTERACTION.interaction_id NULL,
  decision_id FK -> DECISION.decision_id NULL,
  file_path, change_type, origin, confidence,
  lines_added, lines_deleted, line_start, line_end, changed_at
)
```

Stores file-level or line-range change metadata. Nullable links are
intentional: - `commit_id` is null if the change is not yet committed. -
`interaction_id` is null if no AI interaction is linked, for example for
a human-written change. - `decision_id` is null if no decision has been
recorded.

### Relationship summary

  -----------------------------------------------------------------------
  Relationship                        Meaning
  ----------------------------------- -----------------------------------
  USER --- PROJECT                    M:N through `PROJECT_MEMBER`

  USER --- PROJECT_MEMBER             One user may have many membership
                                      rows

  PROJECT --- PROJECT_MEMBER          One project may have many
                                      membership rows

  PROJECT_MEMBER --- AI_INTERACTION   A membership may have many
                                      interactions

  PROJECT_MEMBER --- COMMIT           A membership may have many commits

  PROJECT --- DECISION                One project may have many decisions

  AI_INTERACTION --- DECISION         An interaction may be linked to
                                      decisions; a decision may be manual

  DECISION --- DECISION               Recursive replacement relationship

  DECISION --- ALTERNATIVE            One decision may have many
                                      alternatives

  DECISION --- EVIDENCE               One decision may have many evidence
                                      records

  COMMIT --- CODE_CHANGE              One commit may contain many code
                                      changes

  AI_INTERACTION --- CODE_CHANGE      One interaction may be linked to
                                      many changes

  DECISION --- CODE_CHANGE            One decision may be linked to many
                                      changes
  -----------------------------------------------------------------------

### Integrity rules

-   `PROJECT_MEMBER` uses composite PK `(project_id, user_id)`.
-   `AI_INTERACTION` and `COMMIT` use composite membership FKs.
-   `DECISION.replaced_by_decision_id` references
    `DECISION.decision_id`.
-   Nullable provenance FKs allow incomplete but honest records.
-   Use restrictive deletion or controlled archival for historical
    records; avoid accidental cascading deletion of provenance.
-   Add indexes to common join and lookup fields based on actual query
    patterns.

## AI and NLP Integration

NLP is a supporting extraction layer, not the authority on what
happened.

**Inputs:** AI prompts/responses, developer notes, commit messages, and
other explicitly supported development text.

**Candidate extraction:** identify potential decisions, stated reasons,
alternatives, file/commit references, and semantically similar existing
decisions. Sentence embeddings can support candidate retrieval;
similarity alone does not prove two statements represent the same
decision.

**Validation policy:** 1. NLP produces candidate fields. 2. The source
text/reference remains available. 3. The candidate is checked against
project context and database constraints. 4. A developer approves,
edits, or rejects it. 5. Approved data is stored as an official record.
6. Missing rationale is `UNKNOWN`; inferred rationale remains labelled
`INFERRED`.

Keep candidate extraction separate from developer-approved records.

## Git and Code-Change Provenance

Git provides commits and diffs; this system connects available metadata
to AI interactions and decisions.

A Git collector or hook can record commit hash, message, author/project
membership, and timestamp. Diff processing can provide file paths,
change types, line counts, and line ranges. An editor integration can
associate interactions with files when the selected tool exposes enough
information.

Planned `CODE_CHANGE.origin` values:

  -----------------------------------------------------------------------
  Value                               Meaning
  ----------------------------------- -----------------------------------
  `ai_exact`                          Direct evidence supports the AI
                                      interaction association

  `ai_inferred`                       The association is inferred and
                                      uncertainty remains visible

  `human`                             The change is recorded as
                                      human-written
  -----------------------------------------------------------------------

Do not claim exact line-level attribution when the integration only
knows that an interaction occurred around the same time as a file edit.
Attribution accuracy depends on the evidence available from the selected
integration.

## MCP / AI Assistant Interface

Compatible AI coding assistants may retrieve project history through
named operations: - `why_does_this_exist(file, line)` -
`get_active_decisions(project)` - `get_rejected_alternatives(topic)` -
`check_change(description)` - `record_decision(...)` --- submit a
candidate for approval.

Safety rules: - Read-only retrieval by default. - No arbitrary SQL
through the AI interface. - Named operations with validated
parameters. - Project-scoped authorization for every request. - Human
approval before a generated decision becomes an accepted record. -
Return source references and uncertainty when available.

MCP support is an intended integration layer; actual availability
depends on the compatible client and completed implementation.

## Example Queries

These examples illustrate intended questions; they are not a claim that
every UI endpoint already exists.

### Decisions in a project

``` sql
SELECT decision_id, title, status, reason_text, reason_source_type, decided_at
FROM decision
WHERE project_id = :project_id
ORDER BY decided_at DESC;
```

### Alternatives for a decision

``` sql
SELECT alternative_id, description, selection_status
FROM alternative
WHERE decision_id = :decision_id;
```

### Changes without a linked AI interaction

``` sql
SELECT change_id, file_path, origin, changed_at
FROM code_change
WHERE interaction_id IS NULL;
```

### Trace a change to its commit, interaction, and decision

``` sql
SELECT
  cc.change_id,
  cc.file_path,
  cc.origin,
  c.commit_hash,
  c.message AS commit_message,
  ai.tool_name,
  ai.model_name,
  d.title AS decision_title,
  d.reason_text,
  d.reason_source_type
FROM code_change AS cc
LEFT JOIN git_commit AS c ON c.commit_id = cc.commit_id
LEFT JOIN ai_interaction AS ai ON ai.interaction_id = cc.interaction_id
LEFT JOIN decision AS d ON d.decision_id = cc.decision_id
WHERE cc.change_id = :change_id;
```

This example assumes the physical commit table is named `git_commit`. If
it is named `COMMIT`, quote it consistently in PostgreSQL queries.

## DBMS Concepts Demonstrated

-   ER modelling and relational mapping.
-   Primary keys and foreign keys.
-   Composite primary key in `PROJECT_MEMBER`.
-   Composite membership foreign keys.
-   Self-referencing foreign key for decision replacement.
-   1NF, 2NF, and 3NF normalization.
-   Joins and subqueries for provenance tracing.
-   Views for active decisions and unattributed changes.
-   Functions/procedures for controlled retrieval and decision
    recording.
-   Triggers where they add a clear integrity or audit benefit.
-   Transactions for atomic multi-record operations.
-   Indexes for common joins and lookups.
-   Authorization based on project membership.

Only claim a feature as implemented after it has been built and tested.

## Functional Requirements

1.  Create projects and manage members/roles.
2.  Record AI interactions with prompt/response and tool/model metadata.
3.  Extract candidate decisions, reasons, and alternatives with NLP.
4.  Store decisions with description, type, status, rationale, and
    source interaction.
5.  Store alternatives and selection status.
6.  Store supporting evidence references.
7.  Collect commit metadata and associate it with project members.
8.  Link code changes to commits, interactions, and decisions where
    supported.
9.  Preserve active, rejected, and replaced decision history.
10. Trace code changes to recorded provenance.
11. Maintain referential integrity and use transactions for related
    writes.
12. Restrict provenance access to authorized project members.
13. Retrieve history efficiently as data grows.
14. Preserve timestamps and source references for auditability.
15. Keep NLP, Git, API, and AI-tool integrations modular.

## Non-Functional Requirements

-   **Correctness:** constraints preserve valid relationships and
    statuses.
-   **Transparency:** explicit, inferred, and unknown rationale are
    distinct.
-   **Security:** project-scoped authorization protects data.
-   **Maintainability:** modular components can evolve independently.
-   **Performance:** indexes and query design support common lookups.
-   **Reliability:** transactions prevent partial related writes.
-   **Auditability:** timestamps and references support review.
-   **Extensibility:** new adapters can be added incrementally.

## Scope and Prototype Boundaries

**In scope:** nine-relation PostgreSQL schema, project membership, a
selected interaction-capture path, Git metadata collection, NLP-assisted
candidate extraction, human validation, decision replacement history,
provenance queries, and a dashboard/controlled AI interface as
implemented.

**Not assumed:** universal integration with all AI assistants, perfect
line-level attribution, recovery of rationale that was never recorded,
autonomous approval of NLP output, or production-grade deployment unless
those capabilities are explicitly implemented.

## Suggested Repository Structure

This is a proposed layout; adjust it to match the actual repository.

``` text
intelligent-software-development-provenance/
├── frontend/                 # React dashboard
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── api/               # Routes
│   │   ├── services/          # Business logic
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Request/response validation
│   │   ├── auth/              # Authorization
│   │   └── integrations/      # Git, editor, MCP adapters
│   └── tests/
├── nlp/                       # Extraction and semantic matching
├── database/
│   ├── migrations/
│   ├── schema.sql
│   └── queries/
├── git-hooks/
├── docs/                      # ERD, relational mapping, SRS
├── .env.example
└── README.md
```

## Development Setup

Commands must be adjusted to the actual repository and dependency files.

### Prerequisites

-   Python compatible with the backend dependencies.
-   Node.js compatible with the frontend.
-   PostgreSQL and Git.
-   Local NLP model files if semantic extraction is enabled.

### Create the database

``` sql
CREATE DATABASE provenance_db;
CREATE USER provenance_app WITH PASSWORD 'replace-with-a-local-secret';
GRANT CONNECT ON DATABASE provenance_db TO provenance_app;
```

After connecting to `provenance_db`, grant the required schema/table
privileges and apply the project's migrations. Do not commit real
passwords.

### Environment configuration

Create a local `.env` from `.env.example`, for example:

``` dotenv
DATABASE_URL=postgresql://provenance_app:replace-me@localhost:5432/provenance_db
APP_ENV=development
```

Keep `.env` out of version control.

### Backend

Create and activate a Python virtual environment, then install the
dependencies declared by the repository:

``` bash
python -m venv .venv
pip install -r requirements.txt
```

This assumes `requirements.txt` exists. If the project uses another
dependency manager, use its manifest/lockfile.

A typical FastAPI development command, if the entry point is
`app.main:app`, is:

``` bash
uvicorn app.main:app --reload
```

Use the actual module path from the implementation.

### Frontend

From the frontend directory, install dependencies and run the project's
development script, commonly:

``` bash
npm install
npm run dev
```

### Integration and smoke test

Configure the selected editor adapter, Git collector, and local NLP
model as applicable. Then: 1. Create a test project and add a member. 2.
Ingest a sample interaction. 3. Extract and review a decision candidate.
4. Approve it and add an alternative/evidence record. 5. Ingest a commit
and code-change record. 6. Run a provenance query. 7. Confirm
unauthorized membership references are rejected and optional provenance
links can remain null.

## Suggested API Responsibilities

These are proposed examples, not guaranteed existing endpoints.

  Operation                                Purpose
  ---------------------------------------- ---------------------------------
  `POST /api/projects`                     Create project
  `POST /api/projects/{id}/members`        Add member
  `POST /api/interactions`                 Ingest interaction
  `POST /api/commits`                      Ingest commit metadata
  `POST /api/code-changes`                 Record change metadata
  `POST /api/decisions/candidates`         Submit NLP candidate for review
  `POST /api/decisions`                    Record approved/manual decision
  `GET /api/projects/{id}/decisions`       Retrieve project decisions
  `GET /api/changes/{id}/provenance`       Retrieve change provenance
  `GET /api/decisions/{id}/alternatives`   Retrieve alternatives
  `GET /api/decisions/{id}/evidence`       Retrieve evidence

Every route should authenticate the caller, enforce project
authorization, validate inputs, and use parameterized database
operations.

## Testing Strategy

### Database tests

-   PK uniqueness and FK enforcement.
-   Duplicate project membership rejection.
-   Interaction/commit membership validation.
-   Valid and invalid decision replacement references.
-   Nullable provenance links.
-   Status and origin constraints.
-   Transaction rollback on failed multi-record writes.

### API tests

-   Malformed payload rejection.
-   Unauthorized project access rejection.
-   Interaction and commit ingestion.
-   Decision approval/rejection.
-   Correct provenance retrieval.

### NLP tests

-   Extract an explicit decision from a sample conversation.
-   Preserve source references.
-   Mark missing rationale `UNKNOWN`.
-   Label inferred rationale `INFERRED`.
-   Ensure candidate extraction is not automatic approval.
-   Test false positives and low-confidence matches.

### Integration tests

-   Trace a code change through commit, interaction, and decision.
-   Replace a decision without deleting historical records.
-   Enforce project scope through the API and MCP interface.

## Limitations and Future Enhancements

Potential future improvements include more editor/AI adapters, richer
diff parsing, improved decision review UI, semantic search over
decisions and evidence, exportable audit reports, redaction and
retention controls, granular permissions, measured NLP/attribution
accuracy, and optional vector search when it provides a clear benefit.
These are future possibilities, not completed features unless
implemented.

## Responsible AI and Privacy

Prompts and code context may contain proprietary information,
credentials, or confidential material. The implementation should
minimize collected data, redact secrets where possible, restrict access
by project, keep credentials out of source control, define retention
policies, preserve source references, distinguish facts from inference,
and require human approval for official decision records.

The system improves traceability and reviewability; it does not
guarantee code correctness or replace human code review.

## Glossary

  -----------------------------------------------------------------------
  Term                                Meaning
  ----------------------------------- -----------------------------------
  Provenance                          Recorded origin and history of a
                                      code change or decision

  AI interaction                      Captured prompt/response exchange
                                      with an AI tool

  Engineering decision                Recorded technical choice with
                                      status and context

  Alternative                         Another approach considered for a
                                      decision

  Evidence                            Source reference supporting a
                                      decision

  Explicit rationale                  Reason directly stated in source
                                      material

  Inferred rationale                  Reason inferred from context and
                                      labelled uncertain

  Unknown rationale                   No sufficiently supported reason is
                                      available

  3NF                                 Third Normal Form

  MCP                                 Model Context Protocol, an
                                      interface for compatible AI clients
                                      to access named tools

  Human validation                    Review and approval of extracted
                                      candidate information
  -----------------------------------------------------------------------

## Project Status

This README documents the intended design, schema, architecture, and
prototype scope. Before release or academic submission, update it with
the actual completed modules, supported integration, verified setup
commands, screenshots, test results, and known limitations.

**Project title:** Intelligent Software Development Provenance System\
**Primary DBMS:** PostgreSQL\
**Core innovation:** evidence-aware provenance linking AI interactions,
engineering decisions, Git commits, and code changes.
