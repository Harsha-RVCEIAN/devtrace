"""
nlp/alternative_extractor.py

Step 2 of the pipeline: identify the options discussed in a conversation and
any explicit mentions of their status (rejected, considered).

Why split into Option Sets and Status Mentions?
----------------------------------------------
People discuss options in two distinct ways:
  1. Option sets: they lay out the menu of choices all at once.
     - Questions: "JWT? or redis session based auth, or mutual TLS?"
     - Declarations: "Options are PostgreSQL, MySQL and MongoDB."
     - Bullets: a list of technologies under an intro heading.
  2. Status mentions: they evaluate individual options one by one.
     - "We ruled out MongoDB because eventual consistency..."
     - "MySQL was also considered as an option."
     - "We chose PostgreSQL instead of MongoDB."

By separating these two, the rule engine can:
  - Know all valid options for a decision (from the option set).
  - Apply explicit evaluations (from status mentions).
  - Automatically mark non-chosen options in a set as implicitly rejected.
"""

from dataclasses import dataclass
import re
from typing import Literal

from nlp.models import Alternative, Evidence, SelectionStatus, Sentence
from nlp.text_utils import (
    clean_option_phrase,
    display_name,
    mentions,
    same_option,
    tokens,
)


OptionSetKind = Literal["question", "list", "bullet_block"]


@dataclass(frozen=True)
class OptionSet:
    """A menu of choices presented together in the conversation."""

    options: list[str]
    sentence: Sentence
    kind: OptionSetKind


@dataclass(frozen=True)
class StatusMention:
    """An explicit evaluation of one option within a sentence."""

    option: str
    status: Literal["rejected", "considered"]
    sentence: Sentence


# --- Patterns for Option Sets ------------------------------------------------

# Introductory line that announces an upcoming list of options / bullets.
INTRO_WORDS = re.compile(
    r"\b(?:options|alternatives|choices|evaluated|considered|approaches|candidates)\b",
    re.IGNORECASE,
)

# Declarative statements listing options: "options are A, B and C", "between A and B"
STATEMENT_LIST_PATTERNS = [
    re.compile(
        r"(?:options|alternatives|choices)(?:\s+(?:are|include|considered|were))?:?\s*(.+)$",
        re.IGNORECASE,
    ),
    re.compile(r"\bbetween\s+([A-Za-z0-9_\-\.\s,]+?\s+(?:and|or)\s+[A-Za-z0-9_\-\.\s]+)", re.IGNORECASE),
    re.compile(r"\beither\s+([A-Za-z0-9_\-\.\s,]+?\s+or\s+[A-Za-z0-9_\-\.\s]+)", re.IGNORECASE),
    re.compile(
        r"\b(?:could use|can use|we have)\s+([A-Za-z0-9_\-\.\s,]+?\s+(?:or|and)\s+[A-Za-z0-9_\-\.\s]+)",
        re.IGNORECASE,
    ),
]

# Framing words to strip from the first segment of an option question.
# "how do we secure our website? JWT?" -> "JWT"
# "which database should we use, postgres or mongo?" -> "postgres"
QUESTION_HEAD_TRIM = re.compile(
    r"^.*?\b(?:use|with|on|to|between|choose|pick|adopt|go with|prefer|stay on|have)\b[\s,:?-]*",
    re.IGNORECASE,
)


def find_option_sets(sentences: list[Sentence]) -> list[OptionSet]:
    """Scan transcript sentences and extract option sets."""
    sets: list[OptionSet] = []
    bullet_buffer: list[Sentence] = []
    bullet_intro_sentence: Sentence | None = None

    def flush_bullet_block() -> None:
        nonlocal bullet_buffer, bullet_intro_sentence
        if len(bullet_buffer) >= 2 and bullet_intro_sentence is not None:
            opts: list[str] = []
            for b_sent in bullet_buffer:
                # Text before any colon or dash
                pre_colon = re.split(r"[:–—]", b_sent.text)[0].strip()
                cleaned = clean_option_phrase(pre_colon)
                if cleaned and len(cleaned.split()) <= 5:
                    if not any(same_option(cleaned, o) for o in opts):
                        opts.append(cleaned)
            if len(opts) >= 2:
                sets.append(
                    OptionSet(
                        options=opts,
                        sentence=bullet_intro_sentence,
                        kind="bullet_block",
                    )
                )
        bullet_buffer = []
        bullet_intro_sentence = None

    for i, s in enumerate(sentences):
        # 1. Handle bullet blocks
        if s.is_bullet:
            if bullet_intro_sentence is None and i > 0:
                prev = sentences[i - 1]
                if INTRO_WORDS.search(prev.text) or prev.text.strip().endswith(":"):
                    bullet_intro_sentence = prev
            if bullet_intro_sentence is not None:
                bullet_buffer.append(s)
            continue
        else:
            flush_bullet_block()

        # 2. Choice questions: contains 'or' / 'vs' / 'versus'
        if s.is_question or "?" in s.text:
            if re.search(r"\b(?:or|vs\.?|versus)\b", s.text, re.IGNORECASE):
                opts = _split_question_options(s.text)
                if len(opts) >= 2:
                    sets.append(OptionSet(options=opts, sentence=s, kind="question"))
                    continue

        # 3. Declarative statement lists
        for pat in STATEMENT_LIST_PATTERNS:
            m = pat.search(s.text)
            if m:
                raw_list = m.group(1)
                tokens_list = re.split(r"[,;]|\b(?:or|and|vs\.?|versus)\b", raw_list, flags=re.IGNORECASE)
                cleaned_opts: list[str] = []
                for tok in tokens_list:
                    cl = clean_option_phrase(tok)
                    if cl and not any(same_option(cl, existing) for existing in cleaned_opts):
                        cleaned_opts.append(cl)
                if len(cleaned_opts) >= 2:
                    sets.append(OptionSet(options=cleaned_opts, sentence=s, kind="list"))
                    break

    flush_bullet_block()
    return sets


def _split_question_options(text: str) -> list[str]:
    """
    Parse an interrogative question into candidate options.
    e.g. 'how do we secure our website? JWT? or redis session based auth, or mutual TLS?'
    """
    raw_segments = re.split(r"[?,;]|\b(?:or|vs\.?|versus)\b", text, flags=re.IGNORECASE)
    cleaned_segments = [seg.strip() for seg in raw_segments if seg.strip()]
    if not cleaned_segments:
        return []

    options: list[str] = []

    # First segment: strip question framing ("how do we secure our website...")
    first = cleaned_segments[0]
    if QUESTION_HEAD_TRIM.search(first):
        first = QUESTION_HEAD_TRIM.sub("", first)
    first_opt = clean_option_phrase(first)
    if first_opt:
        options.append(first_opt)

    # Subsequent segments: strip leading articles/verbs and trailing context
    for seg in cleaned_segments[1:]:
        opt = clean_option_phrase(seg)
        if opt and not any(same_option(opt, o) for o in options):
            options.append(opt)

    return options


# --- Patterns for Status Mentions --------------------------------------------

REJECTED_PATTERNS = [
    re.compile(
        r"\b(?:instead of|rather than|not using|ruled out|rejected|ditch|avoid)\s+([A-Za-z0-9_\-\.\s,]+?)"
        r"(?:\s+(?:because|since|as|so|due to|in order to|to|for|with|given)|[.;?!]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:chose|decided on|selected|went with)\s+[^,.;]+\s+over\s+([A-Za-z0-9_\-\.\s,]+?)"
        r"(?:\s+(?:because|since|as|so|due to|in order to|to|for|with|given)|[.;?!]|$)",
        re.IGNORECASE,
    ),
    re.compile(r"([A-Za-z0-9_\-\.\s]{2,30})\s+(?:was ruled out|is overkill|was rejected)\b", re.IGNORECASE),
]

CONSIDERED_PATTERNS = [
    re.compile(
        r"\b(?:considered|evaluated|looked at)\s+([A-Za-z0-9_\-\.\s,]+?)"
        r"(?:\s+(?:as|for|because|since|but|with|given)|[.;?!]|$)",
        re.IGNORECASE,
    ),
    re.compile(r"([A-Za-z0-9_\-\.\s,]+?)\s+(?:were|was)\s+also considered\b", re.IGNORECASE),
    re.compile(r"\banother option is\s+([^,.;]+)", re.IGNORECASE),
]


def find_status_mentions(sentences: list[Sentence]) -> list[StatusMention]:
    """Scan transcript sentences and extract explicit status mentions."""
    mentions_list: list[StatusMention] = []

    for s in sentences:
        # Check rejected patterns
        for pat in REJECTED_PATTERNS:
            for m in pat.finditer(s.text):
                raw = m.group(1)
                for part in re.split(r"[,/]\s*|\s+\band\b\s+", raw):
                    opt = clean_option_phrase(part)
                    if opt:
                        mentions_list.append(StatusMention(option=opt, status="rejected", sentence=s))

        # Check considered patterns
        for pat in CONSIDERED_PATTERNS:
            for m in pat.finditer(s.text):
                raw = m.group(1)
                for part in re.split(r"[,/]\s*|\s+\band\b\s+", raw):
                    opt = clean_option_phrase(part)
                    if opt:
                        mentions_list.append(StatusMention(option=opt, status="considered", sentence=s))

    return mentions_list


def extract_alternatives(text: str) -> list[Alternative]:
    """
    Backwards compatibility: extract alternatives from a plain text string.
    """
    from nlp.transcript import build_transcript

    sentences = build_transcript([(text, "")])
    option_sets = find_option_sets(sentences)
    status_mentions = find_status_mentions(sentences)

    alts_by_name: dict[str, Alternative] = {}

    for oset in option_sets:
        for opt in oset.options:
            key = opt.lower()
            if key not in alts_by_name:
                alts_by_name[key] = Alternative(
                    description=display_name(opt),
                    selection_status="considered",
                    evidence=Evidence.from_sentence(oset.sentence, "alternative"),
                )

    for sm in status_mentions:
        key = sm.option.lower()
        alts_by_name[key] = Alternative(
            description=display_name(sm.option),
            selection_status=sm.status,
            evidence=Evidence.from_sentence(sm.sentence, "alternative"),
        )

    # Check for selected options
    for s in sentences:
        sel_match = re.search(
            r"\b(?:we chose|we decided on|let's use|went with)\s+([A-Za-z0-9_\-\.\s]{2,30}?)(\s+(?:instead|over|because|since)|[.,]|$)",
            s.text,
            re.IGNORECASE,
        )
        if sel_match:
            cl = clean_option_phrase(sel_match.group(1))
            if cl:
                alts_by_name[cl.lower()] = Alternative(
                    description=display_name(cl),
                    selection_status="selected",
                    evidence=Evidence.from_sentence(s, "decision"),
                )

    return list(alts_by_name.values())
