"""
integrations/ai/adapters/base.py

Shared data structures and interface for AI chat transcript adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParsedConversation:
    """Normalized multi-turn AI conversation ready for DevTrace ingestion."""

    tool_name: str
    model_name: str | None
    turns: list[tuple[str, str]]
    external_session_ref: str | None = None


class BaseTranscriptAdapter(ABC):
    """Abstract parser converting raw exported chat logs into turns."""

    @abstractmethod
    def parse_text(self, raw_text: str) -> ParsedConversation:
        """Parse raw file text into a normalized ParsedConversation."""
