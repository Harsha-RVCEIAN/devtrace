"""
nlp/llm_engine.py

Step 6: Optional LLM-assisted decision extraction engine.

Design principles:
    - Uses standard library `urllib.request` (zero third-party dependencies).
    - Talks to Ollama at `http://localhost:11434/api/chat`.
    - Strict deterministic validation: the LLM is treated as an untrusted
      proposer. Python validates every sentence ID, verifies that cited options
      actually appear in the transcript, recomputes rationale confidence, and
      formats all CandidateDecision objects.
    - An injectable `chat_fn` allows unit testing without a live Ollama daemon.
"""

from dataclasses import dataclass
import json
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from nlp.models import (
    Alternative,
    CandidateDecision,
    Evidence,
    Sentence,
)
from nlp.rationale_extractor import HEDGED_WORDS
from nlp.text_utils import clean_option_phrase, display_name, mentions, same_option, tokens


class LLMUnavailable(Exception):
    """Raised when the local LLM cannot be reached, times out, or returns invalid JSON."""


DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decisions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "chosen_option": {"type": "string"},
              "decision_type": {
                  "type": "string",
                  "enum": ["architecture", "security", "implementation", "infrastructure", "refactor"],
              },
              "decision_sentence_ids": {"type": "array", "items": {"type": "integer"}},
              "rationale_sentence_ids": {"type": "array", "items": {"type": "integer"}},
              "alternatives": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "option": {"type": "string"},
                    "status": {"type": "string", "enum": ["selected", "rejected", "considered"]},
                    "sentence_id": {"type": "integer"},
                  },
                  "required": ["option", "status", "sentence_id"],
                },
              },
            },
            "required": [
                "chosen_option", "decision_type", "decision_sentence_ids",
                "rationale_sentence_ids", "alternatives",
            ],
          },
        },
    },
    "required": ["decisions"],
}

SYSTEM_PROMPT = """You are an architectural decision extractor. Analyze the conversation transcript of numbered sentences.
Identify architectural, security, database, or infrastructure decisions.
Return JSON matching the schema. For each decision, cite the EXACT sentence IDs from the transcript for decisions, rationale, and alternatives."""


def default_ollama_chat(
    url: str,
    payload: dict[str, Any],
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Execute chat request to Ollama HTTP API using stdlib urllib."""
    endpoint = f"{url.rstrip('/')}/api/chat"
    req_data = json.dumps(payload).encode("utf-8")
    req = Request(endpoint, data=req_data, headers={"Content-Type": "application/json"})

    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise LLMUnavailable(f"Failed to communicate with Ollama at {endpoint}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LLMUnavailable(f"Ollama returned invalid JSON: {exc}") from exc


class LLMEngine:
    """LLM-assisted decision extractor with deterministic schema validation."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3:latest",
        timeout_seconds: int = 120,
        chat_fn: Callable[[str, dict[str, Any], int], dict[str, Any]] | None = None,
    ) -> None:
        self.ollama_url = ollama_url
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.chat_fn = chat_fn or default_ollama_chat

    def extract(
        self,
        sentences: list[Sentence],
        project_id: UUID | None = None,
        interaction_id: UUID | None = None,
    ) -> list[CandidateDecision]:
        """Send formatted transcript to LLM and validate proposed decisions."""
        if not sentences:
            return []

        # 1. Format prompt with numbered sentences
        transcript_lines = [
            f"[S{s.id}] (turn {s.turn}, {s.speaker}) {s.text}"
            for s in sentences
        ]
        user_prompt = "Transcript:\n" + "\n".join(transcript_lines)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "format": DECISION_SCHEMA,
            "options": {"temperature": 0},
            "stream": False,
            "keep_alive": "5m",
        }

        # 2. Call LLM
        try:
            response_dict = self.chat_fn(self.ollama_url, payload, self.timeout_seconds)
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            raise LLMUnavailable(f"Failed to communicate with LLM: {exc}") from exc

        content_str = response_dict.get("message", {}).get("content", "")
        if not content_str:
            raise LLMUnavailable("Ollama returned empty response content.")

        try:
            parsed = json.loads(content_str)
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"Failed to parse LLM structured JSON output: {exc}") from exc

        raw_decisions = parsed.get("decisions", [])
        if not isinstance(raw_decisions, list):
            return []

        # 3. Deterministic Validation
        sentence_map = {s.id: s for s in sentences}
        transcript_full_text = " ".join(s.text for s in sentences)
        candidates: list[CandidateDecision] = []

        for raw_dec in raw_decisions:
            if not isinstance(raw_dec, dict):
                continue

            chosen_raw = raw_dec.get("chosen_option", "")
            chosen_opt = clean_option_phrase(chosen_raw)
            if not chosen_opt:
                continue

            # Drop decision if chosen option appears nowhere in transcript
            if not mentions(transcript_full_text, chosen_opt):
                continue

            # Validate decision sentence IDs
            dec_ids = [
                i for i in raw_dec.get("decision_sentence_ids", [])
                if isinstance(i, int) and i in sentence_map
            ]
            if not dec_ids:
                continue

            dec_sentences = [sentence_map[i] for i in dec_ids]
            # Drop decision if every decision sentence is a question
            if all(s.is_question or "?" in s.text for s in dec_sentences):
                continue

            # Confidence: 0.75 if developer sentence cited, 0.60 otherwise
            has_dev_sentence = any(s.speaker == "developer" for s in dec_sentences)
            conf = 0.75 if has_dev_sentence else 0.60

            # Validate rationale sentence IDs
            rat_ids = [
                i for i in raw_dec.get("rationale_sentence_ids", [])
                if isinstance(i, int) and i in sentence_map
            ]
            rat_sentences = [sentence_map[i] for i in rat_ids]

            reason_text = " ".join(s.text for s in rat_sentences) if rat_sentences else None
            if reason_text:
                is_hedged = bool(HEDGED_WORDS.search(reason_text))
                reason_source_type = "INFERRED" if is_hedged else "EXPLICIT"
                reason_conf = 0.60 if is_hedged else 0.80
            else:
                reason_source_type = "UNKNOWN"
                reason_conf = 0.0

            # Validate alternatives
            alts_by_name: dict[str, Alternative] = {}
            seen_selected = False

            raw_alts = raw_dec.get("alternatives", [])
            for raw_alt in raw_alts:
                if not isinstance(raw_alt, dict):
                    continue
                alt_opt = clean_option_phrase(raw_alt.get("option", ""))
                if not alt_opt:
                    continue
                alt_status = raw_alt.get("status", "considered")
                s_id = raw_alt.get("sentence_id")

                # Cite valid sentence where option is mentioned
                alt_sentence = sentence_map.get(s_id) if isinstance(s_id, int) else None
                if alt_sentence and not mentions(alt_sentence.text, alt_opt):
                    # Search transcript for a sentence mentioning it
                    alt_sentence = next(
                        (s for s in sentences if mentions(s.text, alt_opt)),
                        None,
                    )

                if alt_status == "selected":
                    if seen_selected or not same_option(alt_opt, chosen_opt):
                        alt_status = "considered"
                    else:
                        seen_selected = True

                ev = Evidence.from_sentence(alt_sentence, "alternative") if alt_sentence else None
                alts_by_name[alt_opt.lower()] = Alternative(
                    description=display_name(alt_opt),
                    selection_status=alt_status,
                    evidence=ev,
                )

            # Ensure chosen option is in alternatives
            if chosen_opt.lower() not in alts_by_name:
                alts_by_name[chosen_opt.lower()] = Alternative(
                    description=display_name(chosen_opt),
                    selection_status="selected",
                    evidence=Evidence.from_sentence(dec_sentences[0], "decision"),
                )

            status_order = {"selected": 0, "rejected": 1, "considered": 2}
            sorted_alts = sorted(
                alts_by_name.values(),
                key=lambda a: (status_order.get(a.selection_status, 3), a.description.lower()),
            )

            # Collect evidence
            all_evidence: list[Evidence] = []
            for s in dec_sentences:
                all_evidence.append(Evidence.from_sentence(s, "decision"))
            for s in rat_sentences:
                all_evidence.append(Evidence.from_sentence(s, "rationale"))
            for a in sorted_alts:
                if a.evidence and a.evidence not in all_evidence:
                    all_evidence.append(a.evidence)

            title = f"Adopt {display_name(chosen_opt)}"
            desc_type = raw_dec.get("decision_type", "architecture")
            if desc_type not in ("architecture", "security", "implementation", "infrastructure", "refactor"):
                desc_type = "architecture"

            rejected_names = [a.description for a in sorted_alts if a.selection_status == "rejected"]
            if rejected_names:
                summary = f"{display_name(chosen_opt)} was selected over {', '.join(rejected_names)}."
            else:
                summary = f"Selected {display_name(chosen_opt)}."

            candidate = CandidateDecision(
                title=title,
                description=summary,
                decision_type=desc_type,
                chosen_option=display_name(chosen_opt),
                confidence=conf,
                reason_text=reason_text,
                reason_source_type=reason_source_type,
                reason_confidence=reason_conf,
                alternatives=sorted_alts,
                evidence=all_evidence,
                status="proposed",
                project_id=project_id,
                interaction_id=interaction_id,
            )
            candidates.append(candidate)

        return candidates
