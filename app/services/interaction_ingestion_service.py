"""
app/services/interaction_ingestion_service.py

End-to-end transcript ingestion pipeline:
1. Parse raw chat logs (JSON/ChatGPT/Markdown) or structured turns.
2. Persist the AIInteraction row in PostgreSQL.
3. Run the NLP extraction pipeline (rules, llm, or auto).
4. Stage every extracted candidate as Decision(status='proposed'), Alternative, and Evidence.
5. Auto-link matching unlinked CodeChange rows as origin='ai_inferred'.
"""

from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AIInteraction,
    Alternative,
    CodeChange,
    Decision,
    Evidence,
    GitCommit,
)
from app.schemas.code_change import CodeChangeUpdate
from app.schemas.interaction import InteractionCreate
from app.schemas.ingestion import BatchIngestTranscriptRequest, IngestTranscriptRequest
from app.schemas.nlp import TurnInput
from app.services.interaction_service import create_interaction
from app.services.provenance_service import (
    get_code_change_provenance,
    update_code_change_provenance,
)
from integrations.ai.adapters.transcript_parser import parse_transcript, parse_transcript_batch
from nlp.pipeline import extract_decisions


def _format_turns_for_storage(turns: list[tuple[str, str]]) -> tuple[str, str]:
    """Combine multi-turn prompts and responses cleanly into AIInteraction columns."""
    if len(turns) == 1:
        p, r = turns[0]
        return (p or "(uploaded transcript)"), (r or "(no response)")

    prompts = []
    responses = []
    for idx, (p, r) in enumerate(turns, start=1):
        if p:
            prompts.append(f"[Turn {idx}] {p}")
        if r:
            responses.append(f"[Turn {idx}] {r}")
    return "\n\n".join(prompts) or "(uploaded transcript)", "\n\n".join(responses) or "(no response)"


def _match_unlinked_changes(
    db: Session,
    *,
    project_id: UUID,
    commit_id: UUID | None,
    searchable_text: str,
) -> list[CodeChange]:
    """
    Find unlinked CodeChange rows in the project to auto-link.

    - If commit_id is explicitly provided, link all unlinked changes in that commit.
    - Otherwise, link unlinked changes whose file path or filename appears in the
      conversation or extracted decision text.
    """
    stmt = select(CodeChange).where(
        CodeChange.project_id == project_id,
        CodeChange.decision_id.is_(None),
        CodeChange.interaction_id.is_(None),
    )
    if commit_id is not None:
        commit_exists = db.scalar(
            select(GitCommit).where(
                GitCommit.commit_id == commit_id,
                GitCommit.project_id == project_id,
            )
        )
        if commit_exists is None:
            raise ValueError("Selected commit does not exist in this project.")
        return list(db.scalars(stmt.where(CodeChange.commit_id == commit_id)).all())

    lowered = searchable_text.lower()
    candidates = list(db.scalars(stmt).all())
    matched: list[CodeChange] = []
    for change in candidates:
        full_path = change.file_path.lower()
        basename = PurePosixPath(change.file_path).name.lower()
        if full_path in lowered or (len(basename) >= 5 and basename in lowered):
            matched.append(change)
    return matched


def ingest_and_stage_transcript(
    db: Session,
    *,
    project_id: UUID,
    user_id: UUID,
    payload: IngestTranscriptRequest,
) -> dict:
    """Parse, persist interaction, run NLP extraction, stage proposed decisions, and auto-link changes."""
    tool_name = payload.tool_name
    model_name = payload.model_name
    external_ref = payload.external_session_ref

    if payload.turns:
        turns = [(t.prompt.strip(), t.response.strip()) for t in payload.turns]
    else:
        parsed = parse_transcript(
            payload.raw_text or "",
            tool_name=tool_name,
            model_name=model_name,
        )
        turns = parsed.turns
        tool_name = parsed.tool_name or tool_name
        model_name = parsed.model_name or model_name
        external_ref = parsed.external_session_ref or external_ref

    prompt_text, response_text = _format_turns_for_storage(turns)
    interaction = create_interaction(
        db=db,
        interaction_data=InteractionCreate(
            project_id=project_id,
            tool_name=tool_name,
            model_name=model_name or "unknown",
            external_session_ref=external_ref,
            prompt=prompt_text,
            response=response_text,
        ),
        user_id=user_id,
    )

    extraction = extract_decisions(
        turns=turns,
        engine=payload.engine,
        project_id=project_id,
        interaction_id=interaction.interaction_id,
    )

    staged_decisions: list[Decision] = []
    now = datetime.now(timezone.utc)

    decision_status = "active" if payload.auto_approve else "proposed"

    for cand in extraction.candidates:
        decision = Decision(
            project_id=project_id,
            interaction_id=interaction.interaction_id,
            title=cand.title[:250],
            description=cand.description,
            decision_type=cand.decision_type[:80],
            status=decision_status,
            reason_text=cand.reason_text,
            reason_source_type=cand.reason_source_type,
            reason_confidence=cand.reason_confidence,
            decided_at=now,
        )
        db.add(decision)
        db.flush()

        for alt in cand.alternatives:
            db.add(
                Alternative(
                    decision_id=decision.decision_id,
                    description=alt.description,
                    selection_status=alt.selection_status,
                )
            )

        for ev in cand.evidence:
            db.add(
                Evidence(
                    decision_id=decision.decision_id,
                    evidence_type=f"transcript_{ev.role}",
                    source_reference=f"[Turn {ev.turn} | {ev.speaker}] {ev.quote}"[:2000],
                )
            )

        staged_decisions.append(decision)

    db.commit()
    for dec in staged_decisions:
        db.refresh(dec)

    auto_linked_provenance = []
    if payload.auto_link:
        searchable = "\n".join(
            [prompt_text, response_text]
            + [f"{d.title} {d.description}" for d in staged_decisions]
        )
        matched_changes = _match_unlinked_changes(
            db,
            project_id=project_id,
            commit_id=payload.commit_id,
            searchable_text=searchable,
        )
        primary_decision = staged_decisions[0] if staged_decisions else None
        for change in matched_changes:
            conf = (
                round(min(float(extraction.candidates[0].confidence), 0.85), 2)
                if extraction.candidates
                else 0.65
            )
            update_code_change_provenance(
                db,
                change,
                CodeChangeUpdate(
                    interaction_id=interaction.interaction_id,
                    decision_id=primary_decision.decision_id if primary_decision else None,
                    origin="ai_inferred",
                    confidence=conf,
                ),
            )
            prov = get_code_change_provenance(db, change.change_id)
            if prov is not None:
                auto_linked_provenance.append(prov)

    return {
        "interaction_id": interaction.interaction_id,
        "turns_count": len(turns),
        "engine_used": extraction.engine_used,
        "warnings": extraction.warnings,
        "staged_decisions": staged_decisions,
        "auto_linked_changes": auto_linked_provenance,
    }


def ingest_transcript_batch(
    db: Session,
    *,
    user_id: UUID,
    payload: BatchIngestTranscriptRequest,
) -> dict:
    """Ingest multiple AI conversations (from raw export or structured list) in one request."""
    items: list[IngestTranscriptRequest] = []

    if payload.conversations:
        for conv in payload.conversations:
            items.append(
                IngestTranscriptRequest(
                    tool_name=conv.tool_name,
                    model_name=conv.model_name,
                    engine=payload.engine,
                    turns=conv.turns,
                    commit_id=conv.commit_id,
                    auto_link=payload.auto_link,
                    auto_approve=payload.auto_approve,
                )
            )
    else:
        parsed_list = parse_transcript_batch(
            payload.raw_text or "",
            tool_name=payload.tool_name,
            model_name=payload.model_name,
        )
        for parsed in parsed_list:
            items.append(
                IngestTranscriptRequest(
                    tool_name=parsed.tool_name,
                    model_name=parsed.model_name,
                    external_session_ref=parsed.external_session_ref,
                    engine=payload.engine,
                    turns=[TurnInput(prompt=p, response=r) for p, r in parsed.turns],
                    auto_link=payload.auto_link,
                    auto_approve=payload.auto_approve,
                )
            )

    all_decisions: list[Decision] = []
    all_linked: dict[UUID, object] = {}
    all_warnings: list[str] = []
    engine_used = payload.engine

    for item in items:
        res = ingest_and_stage_transcript(
            db,
            project_id=payload.project_id,
            user_id=user_id,
            payload=item,
        )
        engine_used = res["engine_used"]
        all_warnings.extend(res["warnings"])
        all_decisions.extend(res["staged_decisions"])
        for ch in res["auto_linked_changes"]:
            all_linked[ch.change_id] = ch

    return {
        "interactions_count": len(items),
        "engine_used": engine_used,
        "warnings": list(dict.fromkeys(all_warnings)),
        "staged_decisions": all_decisions,
        "auto_linked_changes": list(all_linked.values()),
    }
