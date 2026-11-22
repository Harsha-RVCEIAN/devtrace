"""
nlp/decision_extractor.py

Purpose:
    Core NLP extraction pipeline that analyzes an AI interaction transcript
    and produces a CandidateDecision proposal for developer review.

Core Principle:
    Candidate decisions are ALWAYS generated with status='proposed'.
    They must never be auto-approved into the authoritative DECISION
    table without human developer review.
"""

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from nlp.alternative_extractor import ExtractedAlternative, extract_alternatives
from nlp.rationale_extractor import RationaleExtractionResult, extract_rationale


@dataclass
class CandidateDecision:
    """A proposed engineering decision awaiting human review."""
    title: str
    description: str
    decision_type: str
    status: str = "proposed"
    reason_text: str | None = None
    reason_source_type: str = "UNKNOWN"
    reason_confidence: float = 0.0
    alternatives: list[ExtractedAlternative] = field(default_factory=list)
    project_id: UUID | None = None
    interaction_id: UUID | None = None


# Decision trigger keywords indicating architectural/engineering choices
DECISION_TRIGGERS = [
    re.compile(r"(?:let's use|lets use|we'll use|we will use|we'll go with|let's go with|going with)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:we (?:decided|chose|selected|will use|should use)(?:\s+on|\s+to)?)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:recommend(?:ed)? (?:using|approach is|to))\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:the decision is to|architecture choice:?)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:better to use|opted for|opt for)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
]

# Type classification heuristics
TYPE_KEYWORDS = {
    "security": ["auth", "token", "jwt", "encrypt", "password", "hash", "rbac", "permission", "cors", "session"],
    "architecture": [
        "database", "postgresql", "postgres", "sqlite", "mysql", "mongodb", "schema",
        "microservice", "monolith", "kafka", "redis", "orm", "composite", "db", "storage"
    ],
    "refactor": ["cleanup", "restructure", "deprecate", "rename", "modularize", "dry"],
    "implementation": ["function", "loop", "regex", "endpoint", "query", "validation", "pydantic"],
}


def _infer_decision_type(text: str) -> str:
    """Determine decision category based on domain terminology."""
    lower = text.lower()
    for dtype, keywords in TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return dtype
    return "implementation"


def _extract_title(prompt: str, response: str) -> str:
    """Generate a concise title from the prompt or decision clause."""
    combined = f"{prompt}\n{response}"
    for pattern in DECISION_TRIGGERS:
        match = pattern.search(combined)
        if match:
            candidate = match.group(1).strip()
            for prefix in ["on ", "to "]:
                if candidate.lower().startswith(prefix):
                    candidate = candidate[len(prefix):].strip()
            # Strip trailing causal and comparative clauses
            candidate = re.split(
                r"\s+(?:since|because|due to|so that|as|in order to|to achieve|instead of|rather than|over)\s+",
                candidate,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()
            words = candidate.split()[:4]
            clean_name = " ".join(words).rstrip(".,")
            tech_caps = {
                "sqlite": "SQLite",
                "postgresql": "PostgreSQL",
                "postgres": "PostgreSQL",
                "mysql": "MySQL",
                "mongodb": "MongoDB",
                "redis": "Redis",
                "jwt": "JWT",
            }
            display_name = tech_caps.get(clean_name.lower(), clean_name.title())
            return "Adopt " + display_name

    clean_prompt = prompt.strip().split("\n")[0]
    words = clean_prompt.split()[:7]
    return "Decision: " + " ".join(words).rstrip(".,?")


def extract_candidate_decision(
    prompt: str,
    response: str,
    project_id: UUID | None = None,
    interaction_id: UUID | None = None,
) -> CandidateDecision | None:
    """
    Analyze an AI interaction prompt and response to generate a candidate decision.

    Args:
        prompt: User prompt submitted to the AI tool.
        response: Output produced by the AI model.
        project_id: Optional project UUID context.
        interaction_id: Optional interaction UUID context.

    Returns:
        CandidateDecision | None: Proposed candidate, or None if no decision detected.
    """
    combined_text = f"{prompt}\n{response}"

    # 1. Check if any decision trigger exists
    has_trigger = any(p.search(combined_text) for p in DECISION_TRIGGERS)
    if not has_trigger:
        # No engineering choice was made (casual question or simple lookup)
        return None

    # 2. Extract rationale & source classification
    rationale_res: RationaleExtractionResult = extract_rationale(combined_text)

    # 3. Extract candidate alternatives
    alternatives: list[ExtractedAlternative] = extract_alternatives(combined_text)

    # 4. Generate title & description
    title = _extract_title(prompt, response)
    decision_type = _infer_decision_type(combined_text)

    # Description is a high-level summary of what was chosen
    description = rationale_res.reason_text or prompt.strip().split("\n")[0]

    return CandidateDecision(
        title=title,
        description=description,
        decision_type=decision_type,
        status="proposed",  # Strictly proposed - never auto-approved
        reason_text=rationale_res.reason_text,
        reason_source_type=rationale_res.source_type,
        reason_confidence=rationale_res.confidence,
        alternatives=alternatives,
        project_id=project_id,
        interaction_id=interaction_id,
    )
