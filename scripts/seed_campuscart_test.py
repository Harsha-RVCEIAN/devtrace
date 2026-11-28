"""
scripts/seed_campuscart_test.py

Seeds a realistic 'CampusCart (Test)' project owned by your DevTrace user
(found by --email or --github) with 4 commits + file diffs, and provides
4 realistic multi-turn AI chat transcripts (one per commit, including a
negative-control debugging chat) to evaluate NLP extraction end-to-end.

Usage:
    .venv/bin/python scripts/seed_campuscart_test.py --github <your-github-username>
    .venv/bin/python scripts/seed_campuscart_test.py --email <your-email> --run-nlp
"""

import argparse
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import (
    GitCommit,
    OAuthAccount,
    Project,
    ProjectMember,
    User,
)
from app.schemas.commit import CodeChangeItem, CommitCreate
from app.services.commit_service import ingest_commit_with_changes
from app.services.interaction_ingestion_service import ingest_and_stage_transcript
from app.api.routes.interactions import ProjectTranscriptIngestRequest
from nlp.pipeline import extract_decisions


CAMPUSCART_SCENARIOS = [
    {
        "commit_hash": "1111111111111111111111111111111111111111",
        "message": "feat(auth): replace localStorage JWT with Redis server sessions",
        "days_ago": 5,
        "changes": [
            CodeChangeItem(
                file_path="app/auth/session_store.py",
                change_type="added",
                origin="human",
                lines_added=84,
                lines_deleted=0,
            ),
            CodeChangeItem(
                file_path="app/auth/jwt_middleware.py",
                change_type="deleted",
                origin="human",
                lines_added=0,
                lines_deleted=52,
            ),
        ],
        "tool_name": "ChatGPT",
        "model_name": "gpt-4o",
        "turns": [
            (
                "For CampusCart auth in app/auth/session_store.py, should we stick with JWT in localStorage or switch to Redis server sessions or cookie-based signed tokens?",
                "JWT in localStorage is vulnerable to XSS and hard to revoke on logout. Redis server sessions with HttpOnly cookies let you invalidate sessions immediately.",
            ),
            (
                "Yeah true, let's drop JWT and use Redis server sessions instead because users must be logged out immediately when they revoke a device.",
                "Makes sense. Storing sessions in Redis with an HttpOnly cookie handles immediate revocation cleanly. I'll remove jwt_middleware.py and add session_store.py.",
            ),
        ],
    },
    {
        "commit_hash": "2222222222222222222222222222222222222222",
        "message": "feat(db): model orders and listings in PostgreSQL",
        "days_ago": 4,
        "changes": [
            CodeChangeItem(
                file_path="app/db/order_models.py",
                change_type="added",
                origin="human",
                lines_added=112,
                lines_deleted=0,
            ),
        ],
        "tool_name": "Claude",
        "model_name": "claude-3.5-sonnet",
        "turns": [
            (
                "We are starting the database schema for CampusCart orders in app/db/order_models.py. Should we use MongoDB or PostgreSQL or DynamoDB?",
                "Since CampusCart handles marketplace orders, inventory locks, and user balances, PostgreSQL gives you ACID transactions and foreign keys that prevent orphan orders.",
            ),
            (
                "Agreed, let's go with PostgreSQL rather than MongoDB since we need strong ACID transactions and foreign key constraints across orders and listings.",
                "Great choice. PostgreSQL relational schemas will enforce referential integrity cleanly across order_models.py.",
            ),
        ],
    },
    {
        "commit_hash": "3333333333333333333333333333333333333333",
        "message": "perf(listings): switch feed endpoint to cursor pagination",
        "days_ago": 2,
        "changes": [
            CodeChangeItem(
                file_path="app/api/listings.py",
                change_type="modified",
                origin="human",
                lines_added=29,
                lines_deleted=14,
            ),
        ],
        "tool_name": "Cursor",
        "model_name": "claude-3.5-sonnet",
        "turns": [
            (
                "GET /listings in app/api/listings.py is slowing down past page 50. Should we keep OFFSET pagination or move to cursor-based pagination?",
                "OFFSET scans and discards all preceding rows on deep pages and can duplicate items when new listings are posted.",
            ),
            (
                "Okay, let's use cursor-based pagination instead of OFFSET pagination because deep pages are scanning too many rows.",
                "Cursor pagination keyed on `(created_at, listing_id)` will keep query latency constant regardless of page depth.",
            ),
        ],
    },
    {
        "commit_hash": "4444444444444444444444444444444444444444",
        "message": "docs: clarify local dev port in README.md",
        "days_ago": 1,
        "changes": [
            CodeChangeItem(
                file_path="README.md",
                change_type="modified",
                origin="human",
                lines_added=3,
                lines_deleted=2,
            ),
        ],
        "tool_name": "ChatGPT",
        "model_name": "gpt-4o-mini",
        "turns": [
            (
                "Wait why is uvicorn throwing Address already in use on port 8000 when I start the server?",
                "Another process is already bound to port 8000. Run `ss -tlnp | grep 8000` or start uvicorn with `--port 8001`.",
            ),
            (
                "Oh nice, killed the old process and updated the typo in README.md.",
                "Glad that fixed it!",
            ),
        ],
    },
]


def evaluate_nlp_scenarios() -> None:
    """Run all 4 realistic CampusCart transcripts through nlp.pipeline.extract_decisions without DB."""
    for idx, sc in enumerate(CAMPUSCART_SCENARIOS, start=1):
        res = extract_decisions(turns=sc["turns"], engine="rules")
        print(f"\n=== Scenario {idx}: {sc['message']} ===")
        print(f"Candidates extracted: {len(res.candidates)}")
        for c in res.candidates:
            print(f"  Title: {c.title} (type={c.decision_type}, conf={c.confidence:.2f})")
            print(f"  Rationale [{c.reason_source_type} | {c.reason_confidence:.2f}]: {c.reason_text}")
            print(f"  Alternatives: {[(a.description, a.selection_status) for a in c.alternatives]}")
            print(f"  Evidence quotes: {len(c.evidence)}")


def seed_for_user(email: str | None, github_username: str | None, run_nlp: bool) -> None:
    db = SessionLocal()
    try:
        user = None
        if email:
            user = db.scalar(select(User).where(User.email == email.strip().lower()))
        elif github_username:
            oauth = db.scalar(
                select(OAuthAccount).where(
                    OAuthAccount.provider == "github",
                    OAuthAccount.provider_username == github_username.strip(),
                )
            )
            if oauth:
                user = db.scalar(select(User).where(User.user_id == oauth.user_id))
        else:
            user = db.scalar(select(User).order_by(User.created_at.desc()))

        if user is None:
            raise SystemExit("No matching DevTrace user found. Sign in once first, or pass --email / --github.")

        project = db.scalar(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.project_id)
            .where(
                ProjectMember.user_id == user.user_id,
                Project.project_name == "CampusCart (Test)",
            )
        )
        if project is None:
            project = Project(
                project_id=uuid4(),
                project_name="CampusCart (Test)",
                description="Realistic seeded commits + AI chats for testing NLP extraction & provenance linking.",
                repository_url=None,
            )
            db.add(project)
            db.flush()
            db.add(ProjectMember(project_id=project.project_id, user_id=user.user_id, role="owner"))
            db.commit()
            db.refresh(project)

        existing_hashes = set(
            db.scalars(select(GitCommit.commit_hash).where(GitCommit.project_id == project.project_id)).all()
        )
        now = datetime.now(timezone.utc)
        seeded_commits = []

        for sc in CAMPUSCART_SCENARIOS:
            if sc["commit_hash"] in existing_hashes:
                commit = db.scalar(
                    select(GitCommit).where(
                        GitCommit.project_id == project.project_id,
                        GitCommit.commit_hash == sc["commit_hash"],
                    )
                )
                seeded_commits.append((commit, sc))
                continue

            commit = ingest_commit_with_changes(
                db,
                CommitCreate(
                    project_id=project.project_id,
                    commit_hash=sc["commit_hash"],
                    message=sc["message"],
                    commit_time=now - timedelta(days=sc["days_ago"]),
                    changes=sc["changes"],
                ),
                user_id=user.user_id,
            )
            seeded_commits.append((commit, sc))

        print(f"Seeded '{project.project_name}' (id={project.project_id}) for user {user.name} ({user.email}).")

        if run_nlp:
            for commit, sc in seeded_commits:
                res = ingest_and_stage_transcript(
                    db,
                    project_id=project.project_id,
                    user_id=user.user_id,
                    payload=ProjectTranscriptIngestRequest(
                        project_id=project.project_id,
                        tool_name=sc["tool_name"],
                        model_name=sc["model_name"],
                        engine="rules",
                        turns=[{"prompt": p, "response": r} for p, r in sc["turns"]],
                        commit_id=commit.commit_id if commit else None,
                        auto_link=True,
                    ),
                )
                print(
                    f"  -> Commit {sc['commit_hash'][:7]}: staged {len(res['staged_decisions'])} decision(s), "
                    f"auto-linked {len(res['auto_linked_changes'])} file(s)"
                )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed CampusCart test commits and evaluate realistic NLP chats.")
    parser.add_argument("--email", help="Target DevTrace user email")
    parser.add_argument("--github", help="Target DevTrace GitHub username")
    parser.add_argument("--run-nlp", action="store_true", help="Also ingest & auto-link the 4 test chats into DB")
    parser.add_argument("--eval-only", action="store_true", help="Run NLP pipeline offline without touching DB")
    args = parser.parse_args()

    if args.eval_only:
        evaluate_nlp_scenarios()
    else:
        seed_for_user(args.email, args.github, args.run_nlp)
