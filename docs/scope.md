@'
# DevTrace — Project Scope

## Problem
AI-assisted software development history is fragmented across AI conversations, Git commits, code changes, and engineering decisions. Git records code changes but does not necessarily preserve the reasoning or AI interaction behind them.

## MVP
1. Import AI interactions manually through a FastAPI endpoint.
2. Store projects, members, AI interactions, decisions, alternatives, evidence, Git commits, and code changes in PostgreSQL.
3. Link recorded decisions and interactions to code changes when supported by evidence.
4. Record rationale provenance as EXPLICIT, INFERRED, or UNKNOWN.
5. Provide APIs to retrieve project history and trace code changes.
6. Validate inputs, enforce relationships, and test core workflows.

## Stretch Goals
- Integrate one editor or AI coding assistant.
- Automatically collect Git commits and changed-file metadata.
- Use NLP to suggest decisions, reasons, alternatives, and provenance links.
- Build a React dashboard for project history and provenance review.
- Provide a controlled, read-only MCP interface for AI coding tools.

## Explicitly Out of Scope
- Supporting every AI coding tool in the MVP.
- Claiming exact AI authorship without sufficient evidence.
- Automatically approving NLP-generated decisions or inferred rationale.
- Using a separate NoSQL database without a demonstrated need.
- Executing arbitrary SQL through the AI interface.
- Guaranteeing that every code change can be attributed to an AI interaction.

## Technical Stack
- Backend: Python, FastAPI, SQLAlchemy
- Dependency management: uv
- Database: PostgreSQL
- Migrations: Alembic
- Testing: pytest and HTTPX
- Future frontend: React

## Data Integrity and Responsibility
Missing rationale must remain UNKNOWN rather than being fabricated. Inferred provenance must be distinguishable from directly supported links. Sensitive interaction data must be access-controlled, and secrets must not be committed to Git.
