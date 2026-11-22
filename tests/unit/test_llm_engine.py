"""
tests/unit/test_llm_engine.py

Unit tests for the LLM-assisted decision extraction engine.
Uses an injectable fake chat function to verify deterministic validation,
error handling, and schema sanitization without requiring a running Ollama daemon.
"""

import json
import os
from typing import Any
from urllib.error import URLError

import pytest

from nlp.llm_engine import LLMEngine, LLMUnavailable
from nlp.models import Sentence
from nlp.transcript import build_transcript


def make_test_sentences() -> list[Sentence]:
    turns = [
        (
            "how do we secure our website? JWT? or redis session based auth, or mutual TLS?\n"
            "ok i feel like session based auth is the best here",
            "Definitely! it has a simpler lifecycle and safer browser storage.",
        )
    ]
    return build_transcript(turns)


def test_llm_engine_success_with_fake_chat():
    """Verify that a well-formed LLM response is validated and parsed correctly."""
    sentences = make_test_sentences()

    fake_response = {
        "message": {
            "content": json.dumps({
                "decisions": [
                    {
                        "chosen_option": "session based auth",
                        "decision_type": "security",
                        "decision_sentence_ids": [2],
                        "rationale_sentence_ids": [4],
                        "alternatives": [
                            {"option": "session based auth", "status": "selected", "sentence_id": 2},
                            {"option": "JWT", "status": "rejected", "sentence_id": 1},
                            {"option": "mutual TLS", "status": "rejected", "sentence_id": 1},
                        ],
                    }
                ]
            })
        }
    }

    def fake_chat(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        return fake_response

    engine = LLMEngine(chat_fn=fake_chat)
    candidates = engine.extract(sentences)

    assert len(candidates) == 1
    c = candidates[0]
    assert c.title == "Adopt Session Based Auth"
    assert c.decision_type == "security"
    assert c.confidence == 0.75  # Developer sentence cited
    assert c.reason_source_type == "EXPLICIT"
    assert "simpler lifecycle" in (c.reason_text or "")
    assert len(c.alternatives) == 3


def test_llm_engine_raises_unavailable_on_network_error():
    """Verify that connection failures raise LLMUnavailable."""
    sentences = make_test_sentences()

    def failing_chat(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        raise URLError("Connection refused [Errno 111]")

    engine = LLMEngine(chat_fn=failing_chat)
    with pytest.raises(LLMUnavailable):
        engine.extract(sentences)


def test_llm_engine_drops_hallucinated_option():
    """Verify that options not mentioned anywhere in transcript are dropped."""
    sentences = make_test_sentences()

    fake_response = {
        "message": {
            "content": json.dumps({
                "decisions": [
                    {
                        "chosen_option": "Quantum Cryptography",  # Hallucinated
                        "decision_type": "security",
                        "decision_sentence_ids": [1],
                        "rationale_sentence_ids": [],
                        "alternatives": [],
                    }
                ]
            })
        }
    }

    engine = LLMEngine(chat_fn=lambda u, p, t: fake_response)
    candidates = engine.extract(sentences)
    assert len(candidates) == 0


def test_llm_engine_drops_all_question_decision():
    """Verify that if the LLM only cites questions as decision sentences, it is dropped."""
    sentences = make_test_sentences()

    fake_response = {
        "message": {
            "content": json.dumps({
                "decisions": [
                    {
                        "chosen_option": "JWT",
                        "decision_type": "security",
                        "decision_sentence_ids": [0],  # Sentence 0 is a question
                        "rationale_sentence_ids": [],
                        "alternatives": [],
                    }
                ]
            })
        }
    }

    engine = LLMEngine(chat_fn=lambda u, p, t: fake_response)
    candidates = engine.extract(sentences)
    assert len(candidates) == 0


def test_llm_engine_demotes_extra_selected_alternatives():
    """Verify that multiple 'selected' options are demoted to 'considered'."""
    sentences = make_test_sentences()

    fake_response = {
        "message": {
            "content": json.dumps({
                "decisions": [
                    {
                        "chosen_option": "session based auth",
                        "decision_type": "security",
                        "decision_sentence_ids": [2],
                        "rationale_sentence_ids": [],
                        "alternatives": [
                            {"option": "session based auth", "status": "selected", "sentence_id": 2},
                            {"option": "JWT", "status": "selected", "sentence_id": 1},  # Second selected!
                        ],
                    }
                ]
            })
        }
    }

    engine = LLMEngine(chat_fn=lambda u, p, t: fake_response)
    candidates = engine.extract(sentences)
    assert len(candidates) == 1
    alt_map = {a.description.lower(): a.selection_status for a in candidates[0].alternatives}
    assert alt_map.get("jwt") == "considered"


@pytest.mark.skipif(
    os.getenv("DEVTRACE_LLM_TESTS") != "1",
    reason="Live Ollama tests run only when DEVTRACE_LLM_TESTS=1",
)
def test_live_ollama_extraction():
    """Optional integration test against live local Ollama service."""
    sentences = make_test_sentences()
    engine = LLMEngine()
    candidates = engine.extract(sentences)
    assert len(candidates) >= 1
