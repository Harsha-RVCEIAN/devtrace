"""
nlp/decision_extractor.py

Step 4 of the pipeline: scan sentences for statements where a speaker commits to,
prefers, recommends, or accepts an architectural option.

Core principles:
    1. NEVER treat a question as a decision.
    2. Authority and confidence depend on the kind of statement and who said it:
         Developer commit       -> authority 3, conf 0.90
         Developer acceptance   -> authority 3, conf 0.85
         Assistant commit       -> authority 2, conf 0.85
         Developer preference   -> authority 2, conf 0.80
         Assistant recommendation -> authority 1, conf 0.65
         Developer tentative    -> authority 1, conf 0.50
    3. Resolve references:
         "the first/second/last one", "the latter/former", "option 2" map to the
         latest option set.
         "it", "that", "your suggestion" map to the previous recommendation.
"""

from dataclasses import dataclass
import re
from typing import Literal

from nlp.alternative_extractor import OptionSet
from nlp.models import CandidateDecision, Sentence, Speaker
from nlp.text_utils import best_match, clean_option_phrase, same_option


StatementKind = Literal["commit", "preference", "tentative", "recommendation", "acceptance"]


@dataclass(frozen=True)
class DecisionStatement:
    """A statement in the conversation expressing a choice."""

    choice: str
    kind: StatementKind
    authority: int
    confidence: float
    sentence: Sentence
    rejected_option: str | None = None
    target_option_set: OptionSet | None = None


@dataclass(frozen=True)
class StatementPattern:
    """A regex pattern defining how choices are declared in prose."""

    name: str
    pattern: re.Pattern
    kind: StatementKind
    speakers: tuple[Speaker, ...] = ("developer", "assistant")
    needs_option_match: bool = False
    needs_choice_question: bool = False


# Acceptance statements: short developer messages that agree to an assistant recommendation
ACCEPTANCE_REGEX = re.compile(
    r"^(?:(?:ok(?:ay)?|sounds good|agreed|sure|fair|makes sense|go ahead|let's do it|cool|fine)[!.]*\s*)+$",
    re.IGNORECASE,
)

PATTERNS: list[StatementPattern] = [
    # Commits
    StatementPattern(
        name="replace_with",
        pattern=re.compile(r"\breplace\s+(?P<rejected>[A-Za-z0-9_\-\.\s]+?)\s+with\s+(?P<choice>[A-Za-z0-9_\-\.\s]+)", re.IGNORECASE),
        kind="commit",
    ),
    StatementPattern(
        name="migrate_switch_from",
        pattern=re.compile(r"\b(?:migrate|switch)\s+(?:from\s+(?P<rejected>[A-Za-z0-9_\-\.\s]+?)\s+)?to\s+(?P<choice>[A-Za-z0-9_\-\.\s]+)", re.IGNORECASE),
        kind="commit",
    ),
    StatementPattern(
        name="x_it_is",
        pattern=re.compile(r"\b(?P<choice>[A-Za-z0-9_\-\.\s]{2,30})\s+it\s+is\b", re.IGNORECASE),
        kind="commit",
    ),
    StatementPattern(
        name="explicit_commit",
        pattern=re.compile(
            r"\b(?:let's use|lets use|we'll use|we will use|we decided on|we decided to use|we chose|we selected|opted for|going with|go with)\s+"
            r"(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})",
            re.IGNORECASE,
        ),
        kind="commit",
    ),

    # Preferences
    StatementPattern(
        name="feel_like_best",
        pattern=re.compile(
            r"\b(?:i feel like|i think|i believe|in my opinion)\s+(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})\s+is\s+(?:the\s+)?(?:best|better|right|way to go)\b",
            re.IGNORECASE,
        ),
        kind="preference",
        speakers=("developer",),
    ),
    StatementPattern(
        name="sounds_best",
        pattern=re.compile(
            r"\b(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})\s+(?:seems|sounds)\s+like\s+(?:the\s+)?(?:best|better|right)\b",
            re.IGNORECASE,
        ),
        kind="preference",
    ),
    StatementPattern(
        name="better_fit",
        pattern=re.compile(
            r"\b(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})\s+is\s+(?:a\s+)?(?:better|ideal|superior)\s+(?:fit|choice|option)\b",
            re.IGNORECASE,
        ),
        kind="preference",
    ),
    StatementPattern(
        name="i_prefer",
        pattern=re.compile(r"\bi\s+prefer\s+(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})", re.IGNORECASE),
        kind="preference",
        speakers=("developer",),
    ),

    # Tentative
    StatementPattern(
        name="was_thinking",
        pattern=re.compile(
            r"\b(?:i was thinking|was leaning towards|maybe we could use|maybe)\s+(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})",
            re.IGNORECASE,
        ),
        kind="tentative",
        speakers=("developer",),
    ),

    # Recommendations
    StatementPattern(
        name="recommend_suggest",
        pattern=re.compile(
            r"\b(?:i recommend|i suggest|recommendation is to use|we recommend)\s+(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})",
            re.IGNORECASE,
        ),
        kind="recommendation",
        speakers=("assistant",),
    ),
    StatementPattern(
        name="you_should_use",
        pattern=re.compile(
            r"\b(?:you should use|it might be better to use|advisable to use)\s+(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})",
            re.IGNORECASE,
        ),
        kind="recommendation",
        speakers=("assistant",),
    ),
    StatementPattern(
        name="bare_use_recommendation",
        pattern=re.compile(r"^(?:use|adopt)\s+(?P<choice>[A-Za-z0-9_\-\.\s]{2,40})", re.IGNORECASE),
        kind="recommendation",
        speakers=("assistant",),
        needs_choice_question=True,
    ),
]


def _compute_authority_and_conf(kind: StatementKind, speaker: Speaker) -> tuple[int, float]:
    """Return (authority_rank, confidence_score)."""
    if speaker == "developer":
        if kind == "commit":
            return (3, 0.90)
        if kind == "acceptance":
            return (3, 0.85)
        if kind == "preference":
            return (2, 0.80)
        if kind == "tentative":
            return (1, 0.50)
    else:  # assistant
        if kind == "commit":
            return (2, 0.85)
        if kind in ("recommendation", "preference"):
            return (1, 0.65)
    return (1, 0.50)


def _resolve_ordinal_reference(raw_choice: str, option_sets: list[OptionSet]) -> str | None:
    """Resolve 'the latter', 'the former', 'the second one', 'option 1' to option name."""
    if not option_sets:
        return None
    latest_set = option_sets[-1]
    opts = latest_set.options
    if not opts:
        return None

    raw = raw_choice.lower().strip()
    if "former" in raw or "first" in raw or "option 1" in raw:
        return opts[0]
    if "latter" in raw or "last" in raw:
        return opts[-1]
    if "second" in raw or "option 2" in raw:
        return opts[1] if len(opts) > 1 else opts[0]
    if "third" in raw or "option 3" in raw:
        return opts[2] if len(opts) > 2 else None
    return None


def find_decision_statements(
    sentences: list[Sentence],
    option_sets: list[OptionSet],
) -> list[DecisionStatement]:
    """Scan transcript sentences and extract statements declaring choices."""
    statements: list[DecisionStatement] = []
    last_assistant_recommendation: DecisionStatement | None = None

    for i, s in enumerate(sentences):
        # Rule 1: Never treat a question as a decision statement
        if s.is_question or "?" in s.text:
            continue

        # Check for developer acceptance of previous assistant recommendation
        if s.speaker == "developer" and last_assistant_recommendation is not None:
            if ACCEPTANCE_REGEX.match(s.text.strip()):
                auth, conf = _compute_authority_and_conf("acceptance", "developer")
                statements.append(
                    DecisionStatement(
                        choice=last_assistant_recommendation.choice,
                        kind="acceptance",
                        authority=auth,
                        confidence=conf,
                        sentence=s,
                        target_option_set=last_assistant_recommendation.target_option_set,
                    )
                )
                continue

        # Check all statement patterns
        for pat in PATTERNS:
            if s.speaker not in pat.speakers:
                continue

            # Check choice question prerequisite if required
            if pat.needs_choice_question:
                # Find previous developer message
                has_choice_q = False
                for prev in reversed(sentences[:i]):
                    if prev.speaker == "developer":
                        if prev.is_question and any(w in prev.text.lower() for w in ("which", "what", "should", "how", "or")):
                            has_choice_q = True
                        break
                if not has_choice_q and not any(same_option(s.text, o) for oset in option_sets for o in oset.options):
                    continue

            m = pat.pattern.search(s.text)
            if not m:
                continue

            raw_choice = m.group("choice")
            rejected_part = m.group("rejected") if "rejected" in m.groupdict() else None
            cleaned_rejected = clean_option_phrase(rejected_part) if rejected_part else None

            # Check reference resolution
            resolved_choice = _resolve_ordinal_reference(raw_choice, option_sets)
            if resolved_choice is None:
                # Check anaphoric references
                if raw_choice.lower().strip() in ("it", "that", "your suggestion", "the suggestion"):
                    if last_assistant_recommendation:
                        resolved_choice = last_assistant_recommendation.choice

            if resolved_choice is None:
                resolved_choice = clean_option_phrase(raw_choice)

            if not resolved_choice:
                continue

            # Link with matching option set if any, canonicalizing choice to full option name
            matched_set: OptionSet | None = None
            for oset in reversed(option_sets):
                bm = best_match(resolved_choice, oset.options)
                if bm:
                    matched_set = oset
                    resolved_choice = bm
                    break

            auth, conf = _compute_authority_and_conf(pat.kind, s.speaker)
            stmt = DecisionStatement(
                choice=resolved_choice,
                kind=pat.kind,
                authority=auth,
                confidence=conf,
                sentence=s,
                rejected_option=cleaned_rejected,
                target_option_set=matched_set,
            )
            statements.append(stmt)

            if s.speaker == "assistant" and pat.kind in ("recommendation", "commit"):
                last_assistant_recommendation = stmt

            break  # Matched highest priority pattern for this sentence

    return statements


def extract_candidate_decision(
    prompt: str,
    response: str,
    project_id=None,
    interaction_id=None,
) -> CandidateDecision | None:
    """Backwards compatibility: extract decision using the rule engine."""
    from nlp.rule_engine import RuleEngine
    from nlp.transcript import build_transcript

    sentences = build_transcript([(prompt, response)])
    engine = RuleEngine()
    candidates = engine.extract(sentences, project_id=project_id, interaction_id=interaction_id)
    return candidates[0] if candidates else None
