"""
nlp/rationale_extractor.py

Purpose:
    Rule-based extraction and classification of engineering decision rationale
    from AI conversations and development transcripts.

Classification Rules:
    - EXPLICIT: Direct causal statements ('we chose X because Y', 'let's use X since Y', 'the reason is...').
    - INFERRED: Implied or suggested recommendations ('it might be better to...', 'suggests using...').
    - UNKNOWN: No clear rationale found. Never fabricates missing reasoning.
"""

import re
from dataclasses import dataclass
from typing import Literal


ReasonSourceType = Literal["EXPLICIT", "INFERRED", "UNKNOWN"]


@dataclass
class RationaleExtractionResult:
    """Structured extraction result for decision rationale."""
    reason_text: str | None
    source_type: ReasonSourceType
    confidence: float


# Explicit patterns indicating direct human/AI causal rationale
EXPLICIT_PATTERNS = [
    re.compile(
        r"(?:let's use|lets use|we'll use|we will use|we chose|we selected|we decided on|decided to|opted for|opted to|selected|use|going with)\s+"
        r"(.*?)\s+(?:because|due to|since|so that|as|in order to|to achieve)\s+(.*?)(?:\.|\n|$)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:the reason is|rationale is|justification:?)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:in order to|to achieve)\s+(.*?),\s+(?:we (?:use|chose|decided|selected|will use))\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:since|because)\s+(?:it's|it is|we need|they are|this allows|this provides)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
]

# Inferred patterns indicating probabilistic or suggestive reasoning
INFERRED_PATTERNS = [
    re.compile(r"(?:it might be better to|would be preferable to|recommend(?:ed)?)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:suggests using|advisable to|good practice to)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
    re.compile(r"(?:presumably|likely|appears best to)\s+(.*?)(?:\.|\n|$)", re.IGNORECASE),
]


def extract_rationale(text: str) -> RationaleExtractionResult:
    """
    Analyze text to extract rationale and classify source type.

    Args:
        text: Prompt or response text from an AI interaction.

    Returns:
        RationaleExtractionResult: Extracted reason text, source type, and confidence.
    """
    if not text or not text.strip():
        return RationaleExtractionResult(
            reason_text=None,
            source_type="UNKNOWN",
            confidence=0.0,
        )

    clean_text = " ".join(text.split())

    # 1. Check for EXPLICIT rationale patterns
    for pattern in EXPLICIT_PATTERNS:
        match = pattern.search(clean_text)
        if match:
            extracted_reason = match.group(0).strip()
            return RationaleExtractionResult(
                reason_text=extracted_reason,
                source_type="EXPLICIT",
                confidence=0.95,
            )

    # 2. Check for INFERRED rationale patterns
    for pattern in INFERRED_PATTERNS:
        match = pattern.search(clean_text)
        if match:
            extracted_reason = match.group(0).strip()
            return RationaleExtractionResult(
                reason_text=extracted_reason,
                source_type="INFERRED",
                confidence=0.65,
            )

    # 3. Default to UNKNOWN: no rationale claimed when none exists
    return RationaleExtractionResult(
        reason_text=None,
        source_type="UNKNOWN",
        confidence=0.0,
    )
