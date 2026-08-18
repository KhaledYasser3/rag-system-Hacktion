"""
=============================================================================
  MODULAR PDF PARSER — Multi-Signal Heading Detector
=============================================================================
  Combines font size, font weight, numbering patterns, and structural keywords
  to detect headings with high precision.
=============================================================================
"""

from __future__ import annotations

import re
from typing import Tuple, Optional


class HeadingDetector:
    """Multi-signal heading classification engine."""

    NUMBERED_PATTERN = re.compile(r"^(\d+(\.\d+)*)\s+[A-Z]")
    CHAPTER_PATTERN = re.compile(r"^(chapter|section|appendix)\s+[\d\w\.]+", re.IGNORECASE)
    KNOWN_MAJOR_SECTIONS = {
        "contents", "abbreviations", "glossary", "executive summary", "summary",
        "background", "introduction", "methods", "results", "discussion",
        "conclusion", "references", "recommendations", "limitations"
    }

    def detect_heading(self, text: str, avg_font_size: float, body_font_size: float, is_bold: bool) -> Tuple[bool, int, str]:
        """
        Evaluates text line and returns (is_heading, heading_level, prefix).
        heading_level: 1 = Chapter/Major, 2 = Section, 3 = Subsection.
        """
        stripped = text.strip()
        if not stripped:
            return False, 0, ""

        lowered = stripped.lower()

        # 1. Check known major section keywords
        if lowered in self.KNOWN_MAJOR_SECTIONS:
            return True, 1, "## "

        # 2. Check explicit chapter pattern
        if self.CHAPTER_PATTERN.match(stripped):
            return True, 1, "## "

        # 3. Check numbered section pattern (e.g. 3.1. Hypoglycaemic agents)
        if self.NUMBERED_PATTERN.match(stripped) and not stripped.endswith("."):
            level = 2 if stripped.count(".") <= 1 else 3
            prefix = "### " if level == 2 else "#### "
            return True, level, prefix

        # 4. Check font size & weight signals
        if avg_font_size >= body_font_size * 1.35 and not stripped.endswith("."):
            return True, 1, "## "

        if is_bold and avg_font_size >= body_font_size * 1.15 and not stripped.endswith("."):
            return True, 2, "### "

        return False, 0, ""
