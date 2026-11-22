"""
nlp/rationale_extractor.py

Step 3 of the pipeline: find the causal justification for an engineering choice.

Order of priority:
    1. Decision sentence connective (EXPLICIT, 0.95):
       "We chose PostgreSQL because native composite foreign keys provide isolation."
       Look for: because, since, so that, in order to, due to, given that, to ensure/avoid,
       or a colon after the choice.
    2. Nearby justification sentence (EXPLICIT, 0.80):
       Developer: "ok i feel like session based auth is the best here"
       Assistant: "Definitely! it has a simpler lifecycle and safer browser storage."
       Look up to 3 sentences after (skipping conversational filler like "Definitely!")
       or 1 sentence before in the same message.
       Look for: "it/this has/provides/keeps/is simpler...", "we need/want/must...", or
       sentences starting with because/since.
    3. Hedged wording (INFERRED, 0.60):
       "It might be better to use Redis to avoid latency."
       Look for: might, may, probably, likely, perhaps, presumably.
    4. Nothing found (UNKNOWN, 0.0):
       Never hallucinate or synthesize reasons.
"""

from dataclasses import dataclass, field
import re
from typing import Literal

from nlp.models import Evidence, ReasonSourceType, Sentence


@dataclass(frozen=True)
class RationaleResult:
    """The causal reason found for a decision, plus confidence and evidence."""

    reason_text: str | None
    source_type: ReasonSourceType
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)


# Words that introduce a reason inside the decision sentence itself.
INLINE_CAUSAL = re.compile(
    r"\b(?:because|since|so that|in order to|due to|given that|to ensure|to avoid|to achieve)\b|(?<=[:–—])\s*",
    re.IGNORECASE,
)

# Sentences that are pure conversational filler and should be skipped when looking
# for nearby justifications.
FILLER_SENTENCES = re.compile(
    r"^(?:(?:definitely|understood|agreed|sure|great|sounds good|fair|makes sense|got it|cool|nice|okay|ok)[!.]*\s*)+$",
    re.IGNORECASE,
)

# Sentences that state a causal justification.
JUSTIFICATION_LEAD = re.compile(
    r"^(?:(?:because|since|so that|due to|in order to|to ensure|to avoid)\b|"
    r"(?:it|this|they)\s+(?:has|have|provides|provide|offers|offer|keeps|keep|gives|give|is|are|allows|allow)\b|"
    r"(?:we|i)\s+(?:need|want|must|should|require)\b)",
    re.IGNORECASE,
)

# Hedged words indicating inferred / suggestive rationale.
HEDGED_WORDS = re.compile(
    r"\b(?:might|may|probably|likely|perhaps|presumably|could be better|suggests?)\b",
    re.IGNORECASE,
)


def find_rationale(
    decision_sentence: Sentence,
    all_sentences: list[Sentence],
) -> RationaleResult:
    """
    Find the rationale for `decision_sentence` by checking the sentence itself
    and then searching nearby sentences.
    """
    dec_text = decision_sentence.text

    # 1. Check for inline causal connective in the decision sentence itself
    m = INLINE_CAUSAL.search(dec_text)
    if m:
        is_hedged = bool(HEDGED_WORDS.search(dec_text))
        st: ReasonSourceType = "INFERRED" if is_hedged else "EXPLICIT"
        conf = 0.65 if is_hedged else 0.95
        return RationaleResult(
            reason_text=dec_text,
            source_type=st,
            confidence=conf,
            evidence=[Evidence.from_sentence(decision_sentence, "rationale")],
        )

    # 2. Check 1 sentence before in the same message
    dec_idx = decision_sentence.id
    if dec_idx > 0:
        prev_s = all_sentences[dec_idx - 1]
        if prev_s.message_index == decision_sentence.message_index:
            if JUSTIFICATION_LEAD.search(prev_s.text):
                is_hedged = bool(HEDGED_WORDS.search(prev_s.text))
                return RationaleResult(
                    reason_text=prev_s.text,
                    source_type="INFERRED" if is_hedged else "EXPLICIT",
                    confidence=0.60 if is_hedged else 0.80,
                    evidence=[Evidence.from_sentence(prev_s, "rationale")],
                )

    # 3. Check up to 3 sentences after (skipping filler)
    found_justifications: list[Sentence] = []
    checked_count = 0
    next_idx = dec_idx + 1

    while next_idx < len(all_sentences) and checked_count < 3:
        curr = all_sentences[next_idx]
        next_idx += 1
        checked_count += 1

        if FILLER_SENTENCES.match(curr.text.strip()):
            continue

        if JUSTIFICATION_LEAD.search(curr.text):
            found_justifications.append(curr)
            # Take up to 2 closely linked justification sentences
            if len(found_justifications) >= 2:
                break

    if found_justifications:
        combined_text = " ".join(s.text for s in found_justifications)
        is_hedged = any(HEDGED_WORDS.search(s.text) for s in found_justifications)
        st = "INFERRED" if is_hedged else "EXPLICIT"
        conf = 0.60 if is_hedged else 0.80
        ev = [Evidence.from_sentence(s, "rationale") for s in found_justifications]
        return RationaleResult(
            reason_text=combined_text,
            source_type=st,
            confidence=conf,
            evidence=ev,
        )

    # 4. Check if the decision sentence itself was hedged
    if HEDGED_WORDS.search(dec_text):
        return RationaleResult(
            reason_text=dec_text,
            source_type="INFERRED",
            confidence=0.60,
            evidence=[Evidence.from_sentence(decision_sentence, "rationale")],
        )

    # 5. Default to UNKNOWN
    return RationaleResult(
        reason_text=None,
        source_type="UNKNOWN",
        confidence=0.0,
        evidence=[],
    )


def extract_rationale(text: str) -> RationaleResult:
    """Backwards compatibility for unit tests."""
    from nlp.transcript import build_transcript

    sentences = build_transcript([(text, "")])
    if not sentences:
        return RationaleResult(reason_text=None, source_type="UNKNOWN", confidence=0.0)
    return find_rationale(sentences[0], sentences)
