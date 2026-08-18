"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Token Counter Abstraction
=============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger("TokenCounter")


class TokenCounter(ABC):
    """Abstract interface for token counting."""

    @abstractmethod
    def count(self, text: str) -> int:
        """Returns exact or estimated token count for text string."""
        pass


class TiktokenCounter(TokenCounter):
    """Exact token counter using tiktoken encoding (e.g. cl100k_base)."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding_name = encoding_name
        import tiktoken
        self._enc = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._enc.encode(text))


class WordRatioTokenCounter(TokenCounter):
    """Fallback token counter using word-ratio estimation (1 word ≈ 1.3 tokens)."""

    def count(self, text: str) -> int:
        if not text:
            return 0
        return int(len(text.split()) * 1.3)


def get_token_counter(encoding_name: str = "cl100k_base") -> TokenCounter:
    """Factory function for TokenCounter with graceful fallback if tiktoken is missing."""
    try:
        return TiktokenCounter(encoding_name)
    except Exception as e:
        logger.warning(f"Tiktoken unavailable ({e}). Falling back to WordRatioTokenCounter.")
        return WordRatioTokenCounter()
