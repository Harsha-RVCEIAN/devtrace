"""
nlp/pipeline.py

Step 7: The central entry point for the NLP pipeline.

Usage:
    from nlp.pipeline import extract_decisions

    result = extract_decisions(
        turns=[("how do we secure our website? JWT or redis?", "Redis sessions are better")],
        engine="rules",  # "rules" | "llm" | "auto"
    )
    for candidate in result.candidates:
        print(candidate.title, candidate.confidence)
"""

import logging
from typing import Literal
from uuid import UUID

from app.core.config import settings
from nlp.llm_engine import LLMEngine, LLMUnavailable
from nlp.models import ExtractionResult
from nlp.rule_engine import RuleEngine
from nlp.transcript import build_transcript


logger = logging.getLogger(__name__)


def extract_decisions(
    turns: list[tuple[str, str]],
    engine: Literal["rules", "llm", "auto"] = "rules",
    project_id: UUID | None = None,
    interaction_id: UUID | None = None,
) -> ExtractionResult:
    """
    Extract proposed candidate decisions from a multi-turn conversation.

    Args:
        turns: List of (developer_prompt, ai_response) text tuples.
        engine: "rules" (deterministic default), "llm" (local Ollama), or
                "auto" (try LLM with fallback to rules).
        project_id: Optional project context.
        interaction_id: Optional interaction context.

    Returns:
        ExtractionResult containing candidate decisions, engine used, sentences,
        and any warnings generated during extraction.
    """
    sentences = build_transcript(turns)
    if not sentences:
        return ExtractionResult(candidates=[], engine_used="rules", sentences=[], warnings=[])

    rule_eng = RuleEngine()

    if engine == "rules":
        candidates = rule_eng.extract(
            sentences,
            project_id=project_id,
            interaction_id=interaction_id,
        )
        return ExtractionResult(
            candidates=candidates,
            engine_used="rules",
            sentences=sentences,
            warnings=[],
        )

    llm_eng = LLMEngine(
        ollama_url=settings.ollama_url,
        model=settings.nlp_llm_model,
        timeout_seconds=settings.nlp_llm_timeout_seconds,
    )

    if engine == "llm":
        # Raises LLMUnavailable on network/service failure so API route can return 503
        candidates = llm_eng.extract(
            sentences,
            project_id=project_id,
            interaction_id=interaction_id,
        )
        return ExtractionResult(
            candidates=candidates,
            engine_used="llm",
            sentences=sentences,
            warnings=[],
        )

    # engine == "auto"
    try:
        candidates = llm_eng.extract(
            sentences,
            project_id=project_id,
            interaction_id=interaction_id,
        )
        return ExtractionResult(
            candidates=candidates,
            engine_used="llm",
            sentences=sentences,
            warnings=[],
        )
    except LLMUnavailable as exc:
        logger.warning("Local LLM unavailable in auto mode: %s. Falling back to rule engine.", exc)
        candidates = rule_eng.extract(
            sentences,
            project_id=project_id,
            interaction_id=interaction_id,
        )
        return ExtractionResult(
            candidates=candidates,
            engine_used="rules",
            sentences=sentences,
            warnings=[f"Local LLM unavailable ({exc}); fell back to deterministic rule engine."],
        )
