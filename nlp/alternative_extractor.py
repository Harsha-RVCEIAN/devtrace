"""
nlp/alternative_extractor.py

Purpose:
    Rule-based extraction of architectural alternatives and their evaluation
    status (selected, rejected, considered) from AI conversations.

Status Mapping:
    - selected: Option actively chosen ('we selected X', 'let's use X', 'chose X over Y').
    - rejected: Option explicitly discarded ('instead of X', 'rejected X') or non-selected from a candidate list.
    - considered: Option evaluated as an alternative ('considered X', 'alternative was X').
"""

import re
from dataclasses import dataclass
from typing import Literal


AlternativeStatus = Literal["selected", "rejected", "considered"]

STOP_WORDS = {
    "we", "it", "the", "this", "also", "there", "and", "or", "for", "with", "from",
    "here", "are", "our", "you", "they", "that", "these", "those"
}


@dataclass
class ExtractedAlternative:
    """Structured extraction result for a single candidate alternative."""
    description: str
    selection_status: AlternativeStatus


# Regex patterns targeting rejected alternatives
REJECTED_PATTERNS = [
    re.compile(
        r"(?:instead of|rather than|not using|ruled out|rejected)\s+([A-Za-z0-9_\-\.\s]{2,40}?)"
        r"(?:,|\.|\bfor\b|\bbecause\b|\bsince\b|\bin order to\b|\bto achieve\b|\bto\b|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:we (?:discarded|dismissed|opted against))\s+([A-Za-z0-9_\-\.\s]{2,40}?)"
        r"(?:,|\.|\bfor\b|\bbecause\b|\bsince\b|\bin order to\b|\bto achieve\b|\bto\b|$)",
        re.IGNORECASE,
    ),
]

# Regex patterns targeting considered alternatives
CONSIDERED_PATTERNS = [
    re.compile(
        r"(?:considered|evaluated|looked at|we could use|alternative(?:\s+was)?)\s+([A-Za-z0-9_\-\.\s]{2,40}?)"
        r"(?:,|\.|\bfor\b|\bbut\b|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:another option (?:is|was)|possible approach:?)\s+([A-Za-z0-9_\-\.\s]{2,40}?)"
        r"(?:,|\.|\bfor\b|\bbut\b|$)",
        re.IGNORECASE,
    ),
]

# Regex patterns targeting selected alternatives
SELECTED_PATTERNS = [
    re.compile(
        r"(?:let's use|lets use|we'll use|we will use|we chose|we selected|we decided on|decided to use|went with|opt for|going with)\s+"
        r"([A-Za-z0-9_\-\.\s]{2,40}?)"
        r"(?:,|\.|\bbecause\b|\bsince\b|\bfor\b|\bover\b|\binstead of\b|\brather than\b|$)",
        re.IGNORECASE,
    ),
]

# Patterns detecting multi-option listings in earlier paragraphs/sentences
OPTIONS_LIST_PATTERNS = [
    re.compile(
        r"(?:options|alternatives|choices|between|among)(?:\s+(?:are|include|considered|were|for[^\:\n]+))?:?\s*([^\n\.\?]+)",
        re.IGNORECASE,
    ),
]


def extract_alternatives(text: str) -> list[ExtractedAlternative]:
    """
    Scan transcript text to identify alternative options and their status.

    Handles both intra-sentence comparisons ('chose X instead of Y') and
    contextual selection where options were enumerated in a previous paragraph
    or bulleted list and an option was subsequently chosen.

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
            if len(desc) >= 2 and desc.lower() not in seen_descriptions and desc.lower() not in STOP_WORDS:
                seen_descriptions.add(desc.lower())
                found.append(ExtractedAlternative(
                    description=desc,
                    selection_status="rejected",
                ))

    # 2. Search for explicitly selected options
    selected_name: str | None = None
    for pattern in SELECTED_PATTERNS:
        for match in pattern.finditer(clean_text):
            desc = match.group(1).strip()
            if len(desc) >= 2 and desc.lower() not in STOP_WORDS:
                selected_name = desc.lower()
                if desc.lower() not in seen_descriptions:
                    seen_descriptions.add(desc.lower())
                    found.append(ExtractedAlternative(
                        description=desc,
                        selection_status="selected",
                    ))

    # 3. Search for explicitly considered options
    for pattern in CONSIDERED_PATTERNS:
        for match in pattern.finditer(clean_text):
            desc = match.group(1).strip()
            if len(desc) >= 2 and desc.lower() not in seen_descriptions and desc.lower() not in STOP_WORDS:
                seen_descriptions.add(desc.lower())
                found.append(ExtractedAlternative(
                    description=desc,
                    selection_status="considered",
                ))

    # 4. Search for contextual candidate pools (inline options lists or markdown bullet lists)
    list_items: list[str] = []

    # 4a. Inline lists: "options: PostgreSQL, MySQL, SQLite, MongoDB"
    for pattern in OPTIONS_LIST_PATTERNS:
        m = pattern.search(text)
        if m and not m.group(1).lstrip().startswith(("-", "*", "•")):
            tokens = re.split(r"[,;/]|\band\b|\bor\b", m.group(1))
            list_items.extend([t.strip().rstrip(".,") for t in tokens if len(t.strip()) >= 2])

    # 4b. Markdown bullet lists: "- PostgreSQL\n- MySQL\n..."
    bullet_matches = re.findall(
        r"^\s*[-*•\d.]+\s+([A-Za-z0-9_\-\.]{2,30})",
        text,
        flags=re.MULTILINE,
    )
    list_items.extend(bullet_matches)

    # Resolve items from candidate pool
    for item in list_items:
        key = item.lower().strip()
        if key not in seen_descriptions and key not in STOP_WORDS and len(key) >= 2:
            seen_descriptions.add(key)
            if selected_name and selected_name != key:
                # If an option was chosen, other candidates in the pool were rejected
                found.append(ExtractedAlternative(
                    description=item,
                    selection_status="rejected",
                ))
            else:
                found.append(ExtractedAlternative(
                    description=item,
                    selection_status="considered",
                ))

    return found
