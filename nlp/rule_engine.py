"""
nlp/rule_engine.py

Step 5: The deterministic Rule Engine that orchestrates transcript sentences,
option sets, status mentions, decision statements, and rationale into complete
CandidateDecision objects.

Design principles:
    - Pure Python, zero external network calls, sub-millisecond execution.
    - Single forward walk through sentences.
    - Resolves decision updates: a developer's later choice overrides an earlier
      recommendation if authority is higher or equal.
    - Every candidate has status="proposed" and includes full evidence tracing.
"""

from dataclasses import dataclass, field
import re
from uuid import UUID

from nlp.alternative_extractor import (
    OptionSet,
    StatusMention,
    find_option_sets,
    find_status_mentions,
)
from nlp.decision_extractor import DecisionStatement, find_decision_statements
from nlp.models import (
    Alternative,
    CandidateDecision,
    Evidence,
    SelectionStatus,
    Sentence,
)
from nlp.rationale_extractor import find_rationale
from nlp.text_utils import display_name, same_option, tokens


# Domain keyword weights for decision type classification
TYPE_KEYWORDS = {
    "security": [
        "auth", "token", "jwt", "session", "tls", "mtls", "encrypt", "password",
        "hash", "rbac", "permission", "cors", "secret", "cookie", "oauth",
    ],
    "architecture": [
        "database", "postgresql", "postgres", "sqlite", "mysql", "mongodb", "schema",
        "microservice", "monolith", "kafka", "redis", "orm", "composite", "storage",
        "relational", "acid", "nosql",
    ],
    "infrastructure": [
        "docker", "kubernetes", "k8s", "deploy", "render", "aws", "gcp", "ci",
        "cd", "nginx", "server", "linux", "cloud", "host", "container",
    ],
    "refactor": [
        "cleanup", "restructure", "deprecate", "rename", "modularize", "dry", "split",
    ],
    "implementation": [
        "function", "loop", "regex", "endpoint", "query", "validation", "pydantic",
        "pagination", "cursor", "offset", "route", "param",
    ],
}

TYPE_PRIORITY = ["security", "architecture", "infrastructure", "refactor", "implementation"]


@dataclass
class _DecisionDraft:
    """Internal mutable accumulator for building a CandidateDecision."""

    chosen_option: str
    decision_sentence: Sentence
    authority: int
    confidence: float
    target_option_set: OptionSet | None = None
    alternatives: dict[str, Alternative] = field(default_factory=dict)
    decision_sentences: list[Sentence] = field(default_factory=list)

    def add_or_update_alternative(self, alt: Alternative) -> None:
        """Add alternative if not chosen option, resolving duplicates via same_option."""
        if same_option(alt.description, self.chosen_option):
            return

        for key, existing in list(self.alternatives.items()):
            if same_option(alt.description, existing.description):
                # Status priority: selected > rejected > considered
                status_prio = {"selected": 3, "rejected": 2, "considered": 1}
                if status_prio.get(alt.selection_status, 0) >= status_prio.get(existing.selection_status, 0):
                    del self.alternatives[key]
                    self.alternatives[alt.description.lower()] = alt
                return

        self.alternatives[alt.description.lower()] = alt


class RuleEngine:
    """Deterministic rule-based decision extractor."""

    def extract(
        self,
        sentences: list[Sentence],
        project_id: UUID | None = None,
        interaction_id: UUID | None = None,
    ) -> list[CandidateDecision]:
        """Extract candidate decisions from transcript sentences."""
        if not sentences:
            return []

        # 1. Discover option sets and status mentions
        option_sets = find_option_sets(sentences)
        status_mentions = find_status_mentions(sentences)

        # 2. Extract declared decision statements
        statements = find_decision_statements(sentences, option_sets)
        if not statements:
            return []

        # 3. Cluster statements into decisions
        drafts: list[_DecisionDraft] = []

        for stmt in statements:
            matched_draft = self._find_matching_draft(stmt, drafts)

            if matched_draft is None:
                # Create a new decision draft
                draft = _DecisionDraft(
                    chosen_option=stmt.choice,
                    decision_sentence=stmt.sentence,
                    authority=stmt.authority,
                    confidence=stmt.confidence,
                    target_option_set=stmt.target_option_set,
                    decision_sentences=[stmt.sentence],
                )
                drafts.append(draft)
                matched_draft = draft
            else:
                # Decision update / resolution
                matched_draft.decision_sentences.append(stmt.sentence)
                if stmt.authority >= matched_draft.authority:
                    # New choice supersedes earlier choice
                    old_choice = matched_draft.chosen_option
                    if not same_option(old_choice, stmt.choice):
                        # Old choice becomes rejected
                        matched_draft.add_or_update_alternative(
                            Alternative(
                                description=display_name(old_choice),
                                selection_status="rejected",
                                evidence=Evidence.from_sentence(matched_draft.decision_sentence, "alternative"),
                            )
                        )
                    matched_draft.chosen_option = stmt.choice
                    matched_draft.decision_sentence = stmt.sentence
                    matched_draft.authority = stmt.authority
                    matched_draft.confidence = max(matched_draft.confidence, stmt.confidence)
                    if stmt.target_option_set:
                        matched_draft.target_option_set = stmt.target_option_set
                else:
                    # Lower authority statement added as considered if not same option
                    if not same_option(stmt.choice, matched_draft.chosen_option):
                        matched_draft.add_or_update_alternative(
                            Alternative(
                                description=display_name(stmt.choice),
                                selection_status="considered",
                                evidence=Evidence.from_sentence(stmt.sentence, "alternative"),
                            )
                        )

            # Record explicitly rejected option if present in statement
            if stmt.rejected_option:
                matched_draft.add_or_update_alternative(
                    Alternative(
                        description=display_name(stmt.rejected_option),
                        selection_status="rejected",
                        evidence=Evidence.from_sentence(stmt.sentence, "alternative"),
                    )
                )

        # 4. Attach unchosen options from option sets as implicitly rejected
        for draft in drafts:
            if draft.target_option_set:
                for opt in draft.target_option_set.options:
                    if same_option(opt, draft.chosen_option):
                        continue
                    draft.add_or_update_alternative(
                        Alternative(
                            description=display_name(opt),
                            selection_status="rejected",
                            evidence=Evidence.from_sentence(draft.target_option_set.sentence, "alternative"),
                        )
                    )

        # 5. Attach status mentions to matching or nearest draft
        for sm in status_mentions:
            attached_draft = self._find_draft_for_mention(sm, drafts)
            if attached_draft is not None:
                attached_draft.add_or_update_alternative(
                    Alternative(
                        description=display_name(sm.option),
                        selection_status=sm.status,
                        evidence=Evidence.from_sentence(sm.sentence, "alternative"),
                    )
                )

        # 6. Finalize CandidateDecision objects
        candidates: list[CandidateDecision] = []

        for draft in drafts:
            # Add selected option to alternatives list
            draft.alternatives[draft.chosen_option.lower()] = Alternative(
                description=display_name(draft.chosen_option),
                selection_status="selected",
                evidence=Evidence.from_sentence(draft.decision_sentence, "decision"),
            )

            # Find rationale: check primary decision sentence, then any recommendation in draft
            rationale_res = find_rationale(draft.decision_sentence, sentences)
            if rationale_res.source_type == "UNKNOWN":
                for prev_dec_s in reversed(draft.decision_sentences):
                    if prev_dec_s.id != draft.decision_sentence.id:
                        fallback_rat = find_rationale(prev_dec_s, sentences)
                        if fallback_rat.source_type != "UNKNOWN":
                            rationale_res = fallback_rat
                            break

            # Find nearest developer question before decision for context evidence
            context_sentence = self._find_nearest_context_question(draft.decision_sentence, sentences)

            # Classify decision type
            decision_type = self._classify_decision_type(draft, rationale_res.reason_text)

            # Build full evidence list
            all_evidence: list[Evidence] = []
            if context_sentence:
                all_evidence.append(Evidence.from_sentence(context_sentence, "context"))
            for dec_s in draft.decision_sentences:
                all_evidence.append(Evidence.from_sentence(dec_s, "decision"))
            all_evidence.extend(rationale_res.evidence)
            for alt in draft.alternatives.values():
                if alt.evidence and alt.evidence not in all_evidence:
                    all_evidence.append(alt.evidence)

            # Sort alternatives: selected first, then rejected, then considered
            status_order = {"selected": 0, "rejected": 1, "considered": 2}
            sorted_alts = sorted(
                draft.alternatives.values(),
                key=lambda a: (status_order.get(a.selection_status, 3), a.description.lower()),
            )

            # Build title & description
            title = f"Adopt {display_name(draft.chosen_option)}"
            rejected_names = [a.description for a in sorted_alts if a.selection_status == "rejected"]
            if rejected_names:
                summary = f"{display_name(draft.chosen_option)} was selected over {', '.join(rejected_names)}."
            else:
                summary = f"Selected {display_name(draft.chosen_option)}."
            if context_sentence:
                summary = f"{summary} (Context: \"{context_sentence.text}\")"

            candidate = CandidateDecision(
                title=title,
                description=summary,
                decision_type=decision_type,
                chosen_option=display_name(draft.chosen_option),
                confidence=draft.confidence,
                reason_text=rationale_res.reason_text,
                reason_source_type=rationale_res.source_type,
                reason_confidence=rationale_res.confidence,
                alternatives=sorted_alts,
                evidence=all_evidence,
                status="proposed",
                project_id=project_id,
                interaction_id=interaction_id,
            )
            candidates.append(candidate)

        return candidates

    def _find_matching_draft(
        self,
        stmt: DecisionStatement,
        drafts: list[_DecisionDraft],
    ) -> _DecisionDraft | None:
        """Find an existing draft that belongs to the same architectural choice."""
        for draft in drafts:
            # Same target option set
            if stmt.target_option_set and draft.target_option_set:
                if stmt.target_option_set.sentence.id == draft.target_option_set.sentence.id:
                    return draft

            # Matches draft chosen option
            if same_option(stmt.choice, draft.chosen_option):
                return draft

            # Matches any option in draft alternatives
            for alt_name in draft.alternatives:
                if same_option(stmt.choice, alt_name):
                    return draft

            # Target option set contains draft chosen option
            if stmt.target_option_set:
                if any(same_option(opt, draft.chosen_option) for opt in stmt.target_option_set.options):
                    return draft

        return None

    def _find_draft_for_mention(
        self,
        sm: StatusMention,
        drafts: list[_DecisionDraft],
    ) -> _DecisionDraft | None:
        """Find the decision draft that mentions this option, or nearest within 4 sentences."""
        for draft in drafts:
            if same_option(sm.option, draft.chosen_option):
                return draft
            for alt_key in draft.alternatives:
                if same_option(sm.option, alt_key):
                    return draft
            if draft.target_option_set:
                if any(same_option(sm.option, opt) for opt in draft.target_option_set.options):
                    return draft

        # Proximity fallback: nearest draft within 4 sentences
        best_draft: _DecisionDraft | None = None
        min_dist = 5
        for draft in drafts:
            dist = abs(sm.sentence.id - draft.decision_sentence.id)
            if dist < min_dist:
                min_dist = dist
                best_draft = draft

        return best_draft

    def _find_nearest_context_question(
        self,
        decision_sentence: Sentence,
        all_sentences: list[Sentence],
    ) -> Sentence | None:
        """Find the nearest developer question asked before the decision."""
        for s in reversed(all_sentences[:decision_sentence.id]):
            if s.speaker == "developer" and (s.is_question or "?" in s.text):
                return s
        return None

    def _classify_decision_type(
        self,
        draft: _DecisionDraft,
        reason_text: str | None,
    ) -> str:
        """Score domain terminology and return decision type."""
        combined_text = f"{draft.chosen_option} {draft.decision_sentence.text} {reason_text or ''}"
        for alt in draft.alternatives.values():
            combined_text += f" {alt.description}"

        words = tokens(combined_text)
        scores: dict[str, int] = {}
        for dtype, keywords in TYPE_KEYWORDS.items():
            scores[dtype] = sum(1 for kw in keywords if kw in words or any(kw in w for w in words))

        best_score = max(scores.values()) if scores else 0
        if best_score > 0:
            for dtype in TYPE_PRIORITY:
                if scores.get(dtype, 0) == best_score:
                    return dtype

        return "architecture"
