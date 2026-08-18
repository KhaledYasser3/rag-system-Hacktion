"""
=============================================================================
  MODULAR PDF PARSER — Text Cleaner
=============================================================================
  Normalizes whitespace and hyphenation safely without altering semantic content.
=============================================================================
"""

from __future__ import annotations

import re


class TextCleaner:
    """Safely cleans and normalizes text string representations."""

    def clean_text(self, text: str) -> str:
        """Applies whitespace and intra-line hyphenation cleanup."""
        if not text:
            return ""

        # Repair intra-line hyphenation
        cleaned = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
        # Normalize excessive spaces
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)

        return cleaned.strip()
