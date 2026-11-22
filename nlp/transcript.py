"""
nlp/transcript.py

Step 1 of the pipeline: turn a conversation into a flat list of numbered sentences.

    [{prompt, response}, ...]  ──►  [Message, ...]  ──►  [Sentence, ...]

Why sentences? Every later step works one sentence at a time, and every piece of
evidence we output is a sentence quote with its turn number and speaker. Keeping
the original wording (no lowercasing, no rewriting) means quotes stay verbatim.

Splitting rules (deliberately simple):
    1. Fenced code blocks (``` ... ```) are removed: code is not conversation.
    2. Each line is split on its own; bullet lines ("- x", "* x", "1. x") are
       single sentences flagged is_bullet=True, with the marker removed.
    3. Within a line, split after . ! ? when followed by whitespace, EXCEPT
       when the next word is "or"/"and" (so "JWT? or sessions?" stays one
       sentence, which is exactly the list of options we want to keep together)
       and after common abbreviations like "e.g.".
"""

import re

from nlp.models import Message, Sentence, Speaker


CODE_FENCE = re.compile(r"```.*?(?:```|$)", re.DOTALL)
BULLET = re.compile(r"^\s*(?:[-*•+]|\d+[.)])\s+")
HEADING = re.compile(r"^\s*#{1,6}\s+")
MARKDOWN_EMPHASIS = re.compile(r"\*\*|__|`")

# A sentence boundary: end punctuation, then whitespace. The lookahead refuses to
# split when the next word continues a list ("JWT? or sessions").
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?!(?:or|and|vs\.?|versus)\b)", re.IGNORECASE)
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "approx.", "mr.", "dr.")


def messages_from_turns(turns: list[tuple[str, str]]) -> list[Message]:
    """
    Convert UI-style turns [(prompt, response), ...] into ordered Messages.

    Empty sides are skipped, but turn numbers stay aligned with what the user
    typed (turn 1 is always the first pair, even if its response is empty).
    """
    messages: list[Message] = []
    for turn_number, (prompt, response) in enumerate(turns, start=1):
        if prompt and prompt.strip():
            messages.append(Message(turn=turn_number, speaker="developer", text=prompt))
        if response and response.strip():
            messages.append(Message(turn=turn_number, speaker="assistant", text=response))
    return messages


def split_into_sentences(messages: list[Message]) -> list[Sentence]:
    """Split all messages into Sentences with global ids (0, 1, 2, ...)."""
    sentences: list[Sentence] = []
    for message_index, message in enumerate(messages):
        for text, is_bullet in _split_message(message.text):
            sentences.append(
                Sentence(
                    id=len(sentences),
                    turn=message.turn,
                    speaker=message.speaker,
                    text=text,
                    is_question="?" in text,
                    is_bullet=is_bullet,
                    message_index=message_index,
                )
            )
    return sentences


def build_transcript(turns: list[tuple[str, str]]) -> list[Sentence]:
    """Convenience: turns -> messages -> sentences."""
    return split_into_sentences(messages_from_turns(turns))


def _split_message(text: str) -> list[tuple[str, bool]]:
    """Return (sentence_text, is_bullet) pairs for one message."""
    text = CODE_FENCE.sub("\n", text)
    pieces: list[tuple[str, bool]] = []

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        is_bullet = bool(BULLET.match(raw_line))
        line = BULLET.sub("", raw_line)
        line = HEADING.sub("", line)
        line = MARKDOWN_EMPHASIS.sub("", line)
        line = " ".join(line.split())
        if not line:
            continue

        if is_bullet:
            # A bullet is one unit, but long bullets may hold several sentences;
            # keep the first as the bullet and the rest as normal sentences.
            parts = _split_line(line)
            pieces.append((parts[0], True))
            pieces.extend((p, False) for p in parts[1:])
        else:
            pieces.extend((p, False) for p in _split_line(line))

    return pieces


def _split_line(line: str) -> list[str]:
    """Split one line of prose into sentences."""
    parts = SENTENCE_BOUNDARY.split(line)

    # Re-join pieces that were split right after an abbreviation ("e.g. Redis").
    merged: list[str] = []
    for part in parts:
        if merged and merged[-1].lower().endswith(ABBREVIATIONS):
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)

    return [p.strip() for p in merged if p.strip()]
