"""
scripts/seed_demo_data.py

Purpose:
    Idempotent database seeder for DevTrace demonstration data.
    Populates realistic multi-user, multi-project development history
    (CampusCart & LibTrack) matching the lab report specification.

Usage:
    python -m scripts.seed_demo_data
"""

from datetime import datetime, timezone
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import (
    AIInteraction,
    Alternative,
    CodeChange,
    Decision,
    Evidence,
    GitCommit,
    Project,
    ProjectMember,
    User,
)

# ---------------------------------------------------------------------------
# Fixed Canonical UUIDs for Reliable Demonstration
# ---------------------------------------------------------------------------
PROJECT_CAMPUSCART_ID = UUID("d3b07384-d113-4c92-b0b2-320d9f4c3912")
PROJECT_LIBTRACK_ID = UUID("e4c18495-e224-4d03-c1c3-431ea05d4023")

USER_ADITHYA_ID = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
USER_HARSHA_ID = UUID("b1ffcd00-0d1c-4fe9-cc7e-7cc0ce491b22")
USER_KAVYA_ID = UUID("c2aafe11-1e2d-40fa-dd8f-8dd1df502c33")

INTERACTION_1_ID = UUID("11111111-1111-1111-1111-111111111111")
INTERACTION_2_ID = UUID("22222222-2222-2222-2222-222222222222")
INTERACTION_3_ID = UUID("33333333-3333-3333-3333-333333333333")
INTERACTION_4_ID = UUID("44444444-4444-4444-4444-444444444444")
INTERACTION_5_ID = UUID("55555555-5555-5555-5555-555555555555")
INTERACTION_6_ID = UUID("66666666-6666-6666-6666-666666666666")

DECISION_1_ID = UUID("d1000000-0000-0000-0000-000000000001")
DECISION_2_ID = UUID("d1000000-0000-0000-0000-000000000002")
DECISION_3_ID = UUID("d1000000-0000-0000-0000-000000000003")
DECISION_4_ID = UUID("d1000000-0000-0000-0000-000000000004")
DECISION_5_ID = UUID("d1000000-0000-0000-0000-000000000005")
DECISION_6_ID = UUID("d1000000-0000-0000-0000-000000000006")

COMMIT_1_ID = UUID("c1000000-0000-0000-0000-000000000001")
COMMIT_2_ID = UUID("c1000000-0000-0000-0000-000000000002")
COMMIT_3_ID = UUID("c1000000-0000-0000-0000-000000000003")
COMMIT_4_ID = UUID("c1000000-0000-0000-0000-000000000004")
COMMIT_5_ID = UUID("c1000000-0000-0000-0000-000000000005")
COMMIT_6_ID = UUID("c1000000-0000-0000-0000-000000000006")


def seed_database(db: Session) -> None:
    """Populate database with clean demonstration dataset."""
    print("Seeding DevTrace demonstration records...")

    # 1. Users
    users_data = [
        (USER_ADITHYA_ID, "Adithya", "adithya@campuscart.org", "owner"),
        (USER_HARSHA_ID, "Harsha", "harsha@campuscart.org", "contributor"),
        (USER_KAVYA_ID, "Kavya", "kavya@libtrack.org", "owner"),
    ]
    for uid, name, email, role in users_data:
        if not db.get(User, uid):
            db.add(User(user_id=uid, name=name, email=email, role=role))
    db.flush()

    # 2. Projects
    projects_data = [
        (
            PROJECT_CAMPUSCART_ID,
            "CampusCart",
            "Student marketplace for textbooks, supplies, and electronics.",
            "https://github.com/campuscart/core",
        ),
        (
            PROJECT_LIBTRACK_ID,
            "LibTrack",
            "Library book circulation tracking with barcode scanning.",
            "https://github.com/libtrack/mobile",
        ),
    ]
    for pid, pname, pdesc, purl in projects_data:
        if not db.get(Project, pid):
            db.add(Project(project_id=pid, project_name=pname, description=pdesc, repository_url=purl))
    db.flush()

    # 3. Project Members
    memberships = [
        (PROJECT_CAMPUSCART_ID, USER_ADITHYA_ID, "owner"),
        (PROJECT_CAMPUSCART_ID, USER_HARSHA_ID, "contributor"),
        (PROJECT_LIBTRACK_ID, USER_KAVYA_ID, "owner"),
    ]
    for pid, uid, role in memberships:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == pid,
            ProjectMember.user_id == uid,
        )
        if not db.scalar(stmt):
            db.add(ProjectMember(project_id=pid, user_id=uid, role=role))
    db.flush()

    # 4. AI Interactions
    interactions_data = [
        (
            INTERACTION_1_ID,
            PROJECT_CAMPUSCART_ID,
            USER_ADITHYA_ID,
            "ChatGPT",
            "gpt-5",
            "chatgpt-conv-7f3a91",
            "CampusCart has users, listings and orders that reference each other. Should we stay on MongoDB or move to a relational database?",
            "Let us migrate to PostgreSQL because we need stronger relational constraints. MongoDB and MySQL were also considered.",
            datetime(2026, 7, 14, 20, 5, tzinfo=timezone.utc),
        ),
        (
            INTERACTION_2_ID,
            PROJECT_CAMPUSCART_ID,
            USER_ADITHYA_ID,
            "Claude Code",
            "claude-sonnet-5",
            "cc-session-01",
            "Create the PostgreSQL schema for users, listings and orders with foreign keys.",
            "Created db/schema.sql with three tables, primary keys and ON DELETE rules.",
            datetime(2026, 7, 15, 18, 22, tzinfo=timezone.utc),
        ),
        (
            INTERACTION_3_ID,
            PROJECT_CAMPUSCART_ID,
            USER_HARSHA_ID,
            "Claude",
            "claude-opus-5-5",
            "claude-chat-b21e",
            "How should CampusCart handle login for a React frontend and Express API?",
            "Use JWT access tokens with a short expiry, signed on the server and sent in the Authorization header.",
            datetime(2026, 7, 20, 11, 47, tzinfo=timezone.utc),
        ),
        (
            INTERACTION_4_ID,
            PROJECT_CAMPUSCART_ID,
            USER_HARSHA_ID,
            "Claude Code",
            "claude-sonnet-5",
            "cc-session-02",
            "Replace JWT auth with server-side sessions stored in Redis. We need to revoke sessions on logout.",
            "Added src/auth/session.ts using express-session with a Redis store and removed the JWT middleware.",
            datetime(2026, 8, 2, 16, 10, tzinfo=timezone.utc),
        ),
        (
            INTERACTION_5_ID,
            PROJECT_CAMPUSCART_ID,
            USER_ADITHYA_ID,
            "Cursor",
            "claude-sonnet-5",
            "cursor-tab-5521",
            "Add pagination to GET /listings so the home page does not load every listing.",
            "Added cursor-based pagination using the listing id and a limit parameter.",
            datetime(2026, 8, 9, 21, 35, tzinfo=timezone.utc),
        ),
        (
            INTERACTION_6_ID,
            PROJECT_LIBTRACK_ID,
            USER_KAVYA_ID,
            "ChatGPT",
            "gpt-5",
            "chatgpt-conv-c04d12",
            "Which library should LibTrack use to scan book barcodes in a React Native app?",
            "Use ZXing through react-native-vision-camera because it works offline and supports ISBN barcodes.",
            datetime(2026, 8, 11, 19, 0, tzinfo=timezone.utc),
        ),
    ]
    for iid, pid, uid, tool, model, sref, prompt, resp, cat in interactions_data:
        if not db.get(AIInteraction, iid):
            db.add(
                AIInteraction(
                    interaction_id=iid,
                    project_id=pid,
                    user_id=uid,
                    tool_name=tool,
                    model_name=model,
                    external_session_ref=sref,
                    prompt=prompt,
                    response=resp,
                    created_at=cat,
                )
            )
    db.flush()

    # 5. Decisions (insert without replaced_by first to avoid ordering constraint)
    decisions_data = [
        (
            DECISION_1_ID,
            PROJECT_CAMPUSCART_ID,
            INTERACTION_1_ID,
            "Migrate MongoDB to PostgreSQL",
            "Move all CampusCart data to a relational database",
            "architecture",
            "active",
            "Need stronger relational constraints",
            "EXPLICIT",
            0.95,
            datetime(2026, 7, 14, 20, 10, tzinfo=timezone.utc),
        ),
        (
            DECISION_2_ID,
            PROJECT_CAMPUSCART_ID,
            INTERACTION_3_ID,
            "Use JWT for authentication",
            "Stateless JWT access tokens for the API",
            "security",
            "replaced",
            "Simple to use with a React frontend",
            "INFERRED",
            0.68,
            datetime(2026, 7, 20, 11, 55, tzinfo=timezone.utc),
        ),
        (
            DECISION_3_ID,
            PROJECT_CAMPUSCART_ID,
            INTERACTION_4_ID,
            "Use server-side sessions with Redis",
            "Store sessions in Redis instead of issuing JWTs",
            "security",
            "active",
            "Sessions must be revocable on logout",
            "EXPLICIT",
            0.92,
            datetime(2026, 8, 2, 16, 15, tzinfo=timezone.utc),
        ),
        (
            DECISION_4_ID,
            PROJECT_CAMPUSCART_ID,
            INTERACTION_5_ID,
            "Use cursor-based pagination for listings",
            "Paginate GET /listings by listing id",
            "implementation",
            "active",
            "Avoid loading every listing on the home page",
            "EXPLICIT",
            0.88,
            datetime(2026, 8, 9, 21, 40, tzinfo=timezone.utc),
        ),
        (
            DECISION_5_ID,
            PROJECT_CAMPUSCART_ID,
            None,
            "Deploy backend on Render",
            "Host the Express API on Render free tier",
            "architecture",
            "proposed",
            None,
            "UNKNOWN",
            None,
            datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        ),
        (
            DECISION_6_ID,
            PROJECT_LIBTRACK_ID,
            INTERACTION_6_ID,
            "Use ZXing for barcode scanning",
            "Scan ISBN barcodes with ZXing in the mobile app",
            "implementation",
            "active",
            "Works offline and supports ISBN barcodes",
            "EXPLICIT",
            0.90,
            datetime(2026, 8, 11, 19, 5, tzinfo=timezone.utc),
        ),
    ]
    for did, pid, iid, title, desc, dtype, st, rtext, rsource, rconf, dtime in decisions_data:
        d = db.get(Decision, did)
        if not d:
            db.add(
                Decision(
                    decision_id=did,
                    project_id=pid,
                    interaction_id=iid,
                    title=title,
                    description=desc,
                    decision_type=dtype,
                    status=st,
                    reason_text=rtext,
                    reason_source_type=rsource,
                    reason_confidence=rconf,
                    decided_at=dtime,
                )
            )
    db.flush()

    # Link replacement: Decision 2 replaced by Decision 3
    d2 = db.get(Decision, DECISION_2_ID)
    if d2 and d2.replaced_by_decision_id != DECISION_3_ID:
        d2.replaced_by_decision_id = DECISION_3_ID
        d2.status = "replaced"
    db.flush()

    # 6. Alternatives
    alternatives_data = [
        (DECISION_1_ID, "MongoDB", "rejected"),
        (DECISION_1_ID, "MySQL", "rejected"),
        (DECISION_1_ID, "PostgreSQL", "selected"),
        (DECISION_3_ID, "JWT stored in localStorage", "rejected"),
        (DECISION_3_ID, "Redis-backed server sessions", "selected"),
        (DECISION_4_ID, "Offset pagination (LIMIT/OFFSET)", "rejected"),
    ]
    for did, desc, sel_status in alternatives_data:
        stmt = select(Alternative).where(
            Alternative.decision_id == did,
            Alternative.description == desc,
        )
        if not db.scalar(stmt):
            db.add(Alternative(decision_id=did, description=desc, selection_status=sel_status))
    db.flush()

    # 7. Evidence
    evidence_data = [
        (DECISION_1_ID, "ai_interaction", f"interaction_id = {INTERACTION_1_ID}"),
        (DECISION_1_ID, "external_link", "https://www.postgresql.org/docs/current/ddl-constraints.html"),
        (DECISION_2_ID, "ai_interaction", f"interaction_id = {INTERACTION_3_ID}"),
        (DECISION_3_ID, "ai_interaction", f"interaction_id = {INTERACTION_4_ID}"),
        (DECISION_3_ID, "commit", "commit_hash = c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f6"),
        (DECISION_6_ID, "ai_interaction", f"interaction_id = {INTERACTION_6_ID}"),
    ]
    for did, etype, sref in evidence_data:
        stmt = select(Evidence).where(
            Evidence.decision_id == did,
            Evidence.source_reference == sref,
        )
        if not db.scalar(stmt):
            db.add(Evidence(decision_id=did, evidence_type=etype, source_reference=sref))
    db.flush()

    # 8. Git Commits
    commits_data = [
        (
            COMMIT_1_ID,
            PROJECT_CAMPUSCART_ID,
            USER_ADITHYA_ID,
            "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4",
            "Add PostgreSQL schema for users, listings and orders",
            datetime(2026, 7, 15, 18, 40, tzinfo=timezone.utc),
        ),
        (
            COMMIT_2_ID,
            PROJECT_CAMPUSCART_ID,
            USER_HARSHA_ID,
            "b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5",
            "Add JWT login endpoint",
            datetime(2026, 7, 20, 13, 5, tzinfo=timezone.utc),
        ),
        (
            COMMIT_3_ID,
            PROJECT_CAMPUSCART_ID,
            USER_HARSHA_ID,
            "c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f6",
            "Replace JWT with Redis-backed sessions",
            datetime(2026, 8, 2, 16, 40, tzinfo=timezone.utc),
        ),
        (
            COMMIT_4_ID,
            PROJECT_CAMPUSCART_ID,
            USER_ADITHYA_ID,
            "d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f607",
            "Paginate listings API",
            datetime(2026, 8, 9, 22, 0, tzinfo=timezone.utc),
        ),
        (
            COMMIT_5_ID,
            PROJECT_CAMPUSCART_ID,
            USER_ADITHYA_ID,
            "e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718",
            "Fix setup steps in README",
            datetime(2026, 8, 10, 9, 15, tzinfo=timezone.utc),
        ),
        (
            COMMIT_6_ID,
            PROJECT_LIBTRACK_ID,
            USER_KAVYA_ID,
            "f60718293a4b5c6d7e8f90a1b2c3d4e5f6071829",
            "Add barcode scanner screen",
            datetime(2026, 8, 11, 20, 30, tzinfo=timezone.utc),
        ),
    ]
    for cid, pid, uid, chash, cmsg, ctime in commits_data:
        if not db.get(GitCommit, cid):
            db.add(
                GitCommit(
                    commit_id=cid,
                    project_id=pid,
                    user_id=uid,
                    commit_hash=chash,
                    message=cmsg,
                    commit_time=ctime,
                )
            )
    db.flush()

    # 9. Code Changes
    changes_data = [
        (
            UUID("00000000-0000-0000-0000-000000000001"),
            PROJECT_CAMPUSCART_ID,
            COMMIT_1_ID,
            INTERACTION_2_ID,
            DECISION_1_ID,
            "db/schema.sql",
            "added",
            "ai_exact",
            1.00,
            84,
            0,
            1,
            84,
            datetime(2026, 7, 15, 18, 25, tzinfo=timezone.utc),
        ),
        (
            UUID("00000000-0000-0000-0000-000000000002"),
            PROJECT_CAMPUSCART_ID,
            COMMIT_2_ID,
            INTERACTION_3_ID,
            DECISION_2_ID,
            "src/auth/jwt.ts",
            "added",
            "ai_inferred",
            0.83,
            46,
            0,
            1,
            46,
            datetime(2026, 7, 20, 12, 40, tzinfo=timezone.utc),
        ),
        (
            UUID("00000000-0000-0000-0000-000000000003"),
            PROJECT_CAMPUSCART_ID,
            COMMIT_3_ID,
            INTERACTION_4_ID,
            DECISION_3_ID,
            "src/auth/session.ts",
            "added",
            "ai_exact",
            1.00,
            58,
            0,
            1,
            58,
            datetime(2026, 8, 2, 16, 12, tzinfo=timezone.utc),
        ),
        (
            UUID("00000000-0000-0000-0000-000000000004"),
            PROJECT_CAMPUSCART_ID,
            COMMIT_4_ID,
            INTERACTION_5_ID,
            DECISION_4_ID,
            "src/routes/listings.ts",
            "modified",
            "ai_exact",
            1.00,
            31,
            9,
            22,
            61,
            datetime(2026, 8, 9, 21, 38, tzinfo=timezone.utc),
        ),
        (
            UUID("00000000-0000-0000-0000-000000000005"),
            PROJECT_CAMPUSCART_ID,
            COMMIT_5_ID,
            None,
            None,
            "README.md",
            "modified",
            "human",
            None,
            6,
            2,
            14,
            19,
            datetime(2026, 8, 10, 9, 10, tzinfo=timezone.utc),
        ),
        (
            UUID("00000000-0000-0000-0000-000000000006"),
            PROJECT_LIBTRACK_ID,
            COMMIT_6_ID,
            INTERACTION_6_ID,
            DECISION_6_ID,
            "app/screens/ScanScreen.tsx",
            "added",
            "ai_inferred",
            0.78,
            72,
            0,
            1,
            72,
            datetime(2026, 8, 11, 20, 20, tzinfo=timezone.utc),
        ),
    ]
    for chid, pid, cid, iid, did, fpath, ctype, orig, conf, la, ld, ls, le, cat in changes_data:
        if not db.get(CodeChange, chid):
            db.add(
                CodeChange(
                    change_id=chid,
                    project_id=pid,
                    commit_id=cid,
                    interaction_id=iid,
                    decision_id=did,
                    file_path=fpath,
                    change_type=ctype,
                    origin=orig,
                    confidence=conf,
                    lines_added=la,
                    lines_deleted=ld,
                    line_start=ls,
                    line_end=le,
                    changed_at=cat,
                )
            )
    db.commit()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_database(session)
