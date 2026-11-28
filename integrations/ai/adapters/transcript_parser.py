"""
integrations/ai/adapters/transcript_parser.py

Parses uploaded or pasted AI chat exports (JSON arrays, ChatGPT conversations.json,
Markdown/plain-text User:/Assistant: logs) into (prompt, response) turns.
"""

import json
import re
from typing import Any

from integrations.ai.adapters.base import ParsedConversation


_ROLE_LINE_RE = re.compile(
    r"^\s*(?:#{1,4}\s*)?(?:\*\*)?(user|developer|human|prompt|you|assistant|ai|chatgpt|claude|gemini|model|response)(?:\*\*)?\s*:\s*(.*)$",
    re.IGNORECASE,
)

_USER_ROLES = {"user", "developer", "human", "prompt", "you"}
_ASSISTANT_ROLES = {"assistant", "ai", "chatgpt", "claude", "gemini", "model", "response"}


def _pair_role_messages(messages: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Collapse consecutive same-speaker messages and pair into (prompt, response) turns."""
    merged: list[tuple[str, str]] = []
    for role, text in messages:
        clean = text.strip()
        if not clean:
            continue
        if merged and merged[-1][0] == role:
            prev_role, prev_text = merged[-1]
            merged[-1] = (prev_role, f"{prev_text}\n\n{clean}")
        else:
            merged.append((role, clean))

    turns: list[tuple[str, str]] = []
    idx = 0
    while idx < len(merged):
        role, text = merged[idx]
        if role == "user":
            if idx + 1 < len(merged) and merged[idx + 1][0] == "assistant":
                turns.append((text, merged[idx + 1][1]))
                idx += 2
            else:
                turns.append((text, ""))
                idx += 1
        else:
            turns.append(("", text))
            idx += 1

    return [(p, r) for p, r in turns if p or r]


def _extract_chatgpt_mapping(conv: dict[str, Any]) -> ParsedConversation | None:
    """Extract ordered messages from a ChatGPT conversations.json entry."""
    mapping = conv.get("mapping")
    if not isinstance(mapping, dict):
        return None

    chain: list[dict[str, Any]] = []
    node_id = conv.get("current_node")
    visited: set[str] = set()

    if node_id and node_id in mapping:
        while node_id and node_id not in visited:
            visited.add(node_id)
            node = mapping.get(node_id)
            if not node:
                break
            chain.append(node)
            node_id = node.get("parent")
        chain.reverse()
    else:
        chain = list(mapping.values())

    messages: list[tuple[str, str]] = []
    model_name: str | None = None
    for node in chain:
        msg = node.get("message")
        if not isinstance(msg, dict):
            continue
        author = (msg.get("author") or {}).get("role", "").lower()
        if author not in ("user", "assistant"):
            continue
        meta = msg.get("metadata") or {}
        if not model_name and meta.get("model_slug"):
            model_name = str(meta["model_slug"])
        content = msg.get("content") or {}
        parts = content.get("parts") or []
        text_parts = [p for p in parts if isinstance(p, str)]
        text = "\n".join(text_parts).strip()
        if text:
            messages.append((author, text))

    turns = _pair_role_messages(messages)
    if not turns:
        return None
    return ParsedConversation(
        tool_name="ChatGPT",
        model_name=model_name,
        turns=turns,
        external_session_ref=str(conv.get("id") or "") or None,
    )


def _try_parse_json(raw_text: str, tool_name: str, model_name: str | None) -> ParsedConversation | None:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    # 1. ChatGPT conversations.json (list of conversation objects or single object with mapping)
    if isinstance(data, dict) and "mapping" in data:
        parsed = _extract_chatgpt_mapping(data)
        if parsed:
            return parsed

    if isinstance(data, list) and data and isinstance(data[0], dict):
        if "mapping" in data[0]:
            for item in data:
                parsed = _extract_chatgpt_mapping(item)
                if parsed:
                    return parsed

        # 2. List of {prompt, response} objects
        if "prompt" in data[0] or "response" in data[0]:
            turns = [
                (str(item.get("prompt") or "").strip(), str(item.get("response") or "").strip())
                for item in data
                if (str(item.get("prompt") or "").strip() or str(item.get("response") or "").strip())
            ]
            if turns:
                return ParsedConversation(tool_name=tool_name, model_name=model_name, turns=turns)

        # 3. List of {role, content} objects (OpenAI/Anthropic messages array)
        if "role" in data[0] and ("content" in data[0] or "text" in data[0]):
            messages: list[tuple[str, str]] = []
            for item in data:
                role_raw = str(item.get("role") or "").lower()
                role = "user" if role_raw in _USER_ROLES else "assistant" if role_raw in _ASSISTANT_ROLES else ""
                content = item.get("content") if "content" in item else item.get("text")
                if isinstance(content, list):
                    content = "\n".join(
                        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                    )
                if role and content:
                    messages.append((role, str(content)))
            turns = _pair_role_messages(messages)
            if turns:
                return ParsedConversation(tool_name=tool_name, model_name=model_name, turns=turns)

    if isinstance(data, dict) and isinstance(data.get("turns"), list):
        turns = [
            (str(t.get("prompt") or "").strip(), str(t.get("response") or "").strip())
            for t in data["turns"]
            if isinstance(t, dict)
        ]
        turns = [(p, r) for p, r in turns if p or r]
        if turns:
            return ParsedConversation(
                tool_name=str(data.get("tool_name") or tool_name),
                model_name=data.get("model_name") or model_name,
                turns=turns,
            )

    return None


def parse_transcript(
    raw_text: str,
    *,
    tool_name: str = "AI Chat",
    model_name: str | None = None,
) -> ParsedConversation:
    """
    Parse JSON, ChatGPT export, or Markdown/plain-text chat logs into turns.
    """
    stripped = raw_text.strip()
    if not stripped:
        raise ValueError("Transcript text is empty.")

    if stripped.startswith("{") or stripped.startswith("["):
        json_parsed = _try_parse_json(stripped, tool_name, model_name)
        if json_parsed is not None:
            return json_parsed

    # Markdown / plain-text role-prefixed transcript
    messages: list[tuple[str, str]] = []
    current_role: str | None = None
    buffer: list[str] = []

    for line in stripped.splitlines():
        match = _ROLE_LINE_RE.match(line)
        if match:
            if current_role and buffer:
                messages.append((current_role, "\n".join(buffer)))
            label = match.group(1).lower()
            current_role = "user" if label in _USER_ROLES else "assistant"
            first_rest = match.group(2).strip()
            buffer = [first_rest] if first_rest else []
        else:
            if current_role is not None:
                buffer.append(line)

    if current_role and buffer:
        messages.append((current_role, "\n".join(buffer)))

    turns = _pair_role_messages(messages)
    if turns:
        return ParsedConversation(tool_name=tool_name, model_name=model_name, turns=turns)

    # Fallback: treat raw text as a single developer note/prompt
    return ParsedConversation(
        tool_name=tool_name,
        model_name=model_name,
        turns=[(stripped, "Acknowledged.")],
    )


def parse_transcript_batch(
    raw_text: str,
    *,
    tool_name: str = "AI Chat",
    model_name: str | None = None,
) -> list[ParsedConversation]:
    """
    Parse raw text containing one or multiple conversations into a list of ParsedConversation.

    Supports:
    - ChatGPT conversations.json arrays (one ParsedConversation per conversation entry)
    - JSON arrays of {tool_name, turns} objects
    - Markdown/text separated by `---` session dividers
    - Single conversation fallback via parse_transcript
    """
    stripped = raw_text.strip()
    if not stripped:
        raise ValueError("Transcript text is empty.")

    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, list) and data and isinstance(data[0], dict):
                if "mapping" in data[0]:
                    results = [
                        parsed
                        for item in data
                        if (parsed := _extract_chatgpt_mapping(item)) is not None
                    ]
                    if results:
                        return results
                if "turns" in data[0]:
                    results: list[ParsedConversation] = []
                    for item in data:
                        turns = [
                            (str(t.get("prompt") or "").strip(), str(t.get("response") or "").strip())
                            for t in (item.get("turns") or [])
                            if isinstance(t, dict)
                        ]
                        turns = [(p, r) for p, r in turns if p or r]
                        if turns:
                            results.append(
                                ParsedConversation(
                                    tool_name=str(item.get("tool_name") or tool_name),
                                    model_name=item.get("model_name") or model_name,
                                    turns=turns,
                                )
                            )
                    if results:
                        return results
        except json.JSONDecodeError:
            pass

    # Markdown multi-session divider (`---` on its own line)
    if re.search(r"(?m)^\s*---\s*$", stripped):
        sections = [s.strip() for s in re.split(r"(?m)^\s*---\s*$", stripped) if s.strip()]
        if len(sections) > 1:
            return [
                parse_transcript(sec, tool_name=tool_name, model_name=model_name)
                for sec in sections
            ]

    return [parse_transcript(stripped, tool_name=tool_name, model_name=model_name)]
