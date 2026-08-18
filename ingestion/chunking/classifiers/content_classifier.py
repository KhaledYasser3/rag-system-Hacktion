"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Content Classifier
=============================================================================
  Deterministic rule-based classification layer that determines what type of
  content a structural block represents (paragraph, heading, glossary_entry,
  table, list, figure). Does NOT use an LLM.
=============================================================================
"""

from __future__ import annotations

import re
from typing import Any, Dict
from ingestion.chunking.models import ContentType, StructuralBlock


class ContentClassifier:
    """Classifies structural blocks using parser metadata and deterministic rules."""

    # Glossary chapter/section keyword patterns
    GLOSSARY_SECTIONS = re.compile(
        r"\b(glossary|definitions|abbreviations|terms)\b", re.IGNORECASE
    )

    # Bulleted/numbered list pattern
    LIST_PATTERN = re.compile(
        r"^\s*([\-\*\•\d+\.]|\([a-z0-9]+\))\s+", re.MULTILINE
    )

    # Term: Definition or Term \n Definition pattern
    GLOSSARY_ENTRY_PATTERN = re.compile(
        r"^([A-Z0-9][\w\s\-\(\)\/\.,]{2,50})\s*(?::|\n|\s{2,})\s*([A-Z].+)$", re.DOTALL
    )

    def classify(self, node: Any, chapter: str, section: str, subsection: str) -> ContentType:
        """Determines ContentType of a leaf node using node type & context."""
        node_type = getattr(node, "node_type", "")

        # 1. Table node
        if node_type == "Table":
            # Check if this table is actually a formatted glossary box inside Glossary chapter
            if self.is_glossary_context(chapter, section, subsection):
                return ContentType.GLOSSARY_ENTRY
            return ContentType.TABLE

        # 2. Figure node
        if node_type == "Figure":
            return ContentType.FIGURE

        # 3. Heading node
        if node_type in ("Heading", "Chapter", "Appendix", "Section", "Subsection", "Document Title"):
            return ContentType.HEADING

        # 4. Paragraph node evaluation
        if node_type == "Paragraph":
            text = getattr(node, "text", "").strip()

            # Check if in Glossary section
            if self.is_glossary_context(chapter, section, subsection):
                return ContentType.GLOSSARY_ENTRY

            # Check if standalone text exhibits explicit list structure (multiple list items)
            list_matches = self.LIST_PATTERN.findall(text)
            if len(list_matches) >= 2 or (len(list_matches) == 1 and text.startswith(("- ", "* ", "1. "))):
                return ContentType.LIST

            # Check if text matches isolated Term-Definition pattern
            if self.is_standalone_glossary_pattern(text):
                return ContentType.GLOSSARY_ENTRY

            return ContentType.PARAGRAPH

        return ContentType.PARAGRAPH

    def is_glossary_context(self, chapter: str, section: str, subsection: str) -> bool:
        """Return True if node belongs to Glossary/Abbreviations chapter or section."""
        combined = f"{chapter} {section} {subsection}".lower()
        return bool(self.GLOSSARY_SECTIONS.search(combined))

    def is_standalone_glossary_pattern(self, text: str) -> bool:
        """Check if paragraph text matches a standalone term + definition format."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) >= 2 and len(lines[0]) < 60 and not lines[0].endswith("."):
            # First line looks like a term name, second line starts with capital letter definition
            if lines[1][0].isupper() or lines[1].startswith("A ") or lines[1].startswith("The "):
                return True
        return False
