"""
nlp/alternative_extractor.py

Purpose:
    Rule-based extraction of architectural alternatives and their evaluation
    status (selected, rejected, considered) from AI conversations.

Status Mapping:
    - selected: Option actively chosen ('we selected X', 'chose X over Y').
    - rejected: Option explicitly discarded ('instead of X', 'rejected X', 'rather than X').
    - considered: Option evaluated as an alternative ('considered X', 'alternative was X').
"""

import re
from dataclasses import dataclass
from typing import Literal


AlternativeStatus = Literal["selected", "rejected", "considered"]


@dataclass
class ExtractedAlternative:
    """Structured extraction result for a single candidate alternative."""
    description: str
    selection_status: AlternativeStatus


# Regex patterns targeting rejected alternatives
REJECTED_PATTERNS = [
    re.compile(r"(?:instead of|rather than|not using|ruled out|rejected)\s+([A-Za-z0-9_\-\.\s]{2,40}?)(?:,|\.|\bfor\b|\bbecause\b|$)", re.IGNORECASE),
    re.compile(r"(?:we (?:discarded|dismissed|opted against))\s+([A-Za-z0-9_\-\.\s]{2,40}?)(?:,|\.|\bfor\b|\bbecause\b|$)", re.IGNORECASE),
]

# Regex patterns targeting considered alternatives
CONSIDERED_PATTERNS = [
    re.compile(r"(?:considered|evaluated|looked at|we could use|alternative(?:\s+was)?)\s+([A-Za-z0-9_\-\.\s]{2,40}?)(?:,|\.|\bfor\b|\bbut\b|$)", re.IGNORECASE),
    re.compile(r"(?:another option (?:is|was)|possible approach:?)\s+([A-Za-z0-9_\-\.\s]{2,40}?)(?:,|\.|\bfor\b|\bbut\b|$)", re.IGNORECASE),
]

# Regex patterns targeting selected alternatives
SELECTED_PATTERNS = [
    re.compile(r"(?:we (?:chose|selected|decided on|went with))\s+([A-Za-z0-9_\-\.\s]{2,40}?)(?:,|\.|\bbecause\b|\bfor\b|\bover\b|$)", re.IGNORECASE),
]


def extract_alternatives(text: str) -> list[ExtractedAlternative]:
    """
    Scan transcript text to identify alternative options and their status.

    Args:
        text: Prompt or response text from an AI interaction.

    Returns:
        list[ExtractedAlternative]: List of extracted alternatives.
    """
    if not text or not text.strip():
        return []

    clean_text = " ".join(text.split())
    found: list[ExtractedAlternative] = []
    seen_descriptions: set[str] = set()

    # 1. Search for explicitly rejected options
    for pattern in REJECTED_PATTERNS:
        for match in pattern.finditer(clean_text):
            desc = match.group(1).strip()
            # Filter out generic filler words
            if len(desc) >= 3 and desc.lower() not in seen_descriptions and not desc.lower().startswith("it"):
                seen_descriptions.add(desc.lower())
                found.append(ExtractedAlternative(
                    description=desc,
                    selection_status="rejected",
                ))

    # 2. Search for considered options
    for pattern in CONSIDERED_PATTERNS:
        for match in pattern.finditer(clean_text):
            desc = match.group(1).strip()
            if len(desc) >= 3 and desc.lower() not in seen_descriptions and not desc.lower().startswith("it"):
                seen_descriptions.add(desc.lower())
                found.append(ExtractedAlternative(
                    description=desc,
                    selection_status="considered",
                ))

    # 3. Search for selected options
    for pattern in SELECTED_PATTERNS:
        for match in pattern.finditer(clean_text):
            desc = match.group(1).strip()
            if len(desc) >= 3 and desc.lower() not in seen_descriptions and not desc.lower().startswith("it"):
                seen_descriptions.add(desc.lower())
                found.append(ExtractedAlternative(
                    description=desc,
                    selection_status="selected",
                ))

    return found