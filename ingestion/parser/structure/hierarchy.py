"""
=============================================================================
  MODULAR PDF PARSER — Outline Hierarchy Stack
=============================================================================
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple


class HierarchyTracker:
    """Tracks active Chapter -> Section -> Subsection state during page processing."""

    def __init__(self, doc_title: str = "WHO Guidelines"):
        self.doc_title = doc_title
        self.stack: List[Tuple[int, str]] = []  # (level, title)

    def update_heading(self, level: int, title: str) -> None:
        clean_title = title.strip().lstrip("#").strip()
        self.stack = [item for item in self.stack if item[0] < level]
        self.stack.append((level, clean_title))

    def get_current_metadata(self) -> Dict[str, str]:
        ch, sec, sub = "General Context", "General Section", "General Subsection"
        for level, title in self.stack:
            if level == 1:
                ch = title
            elif level == 2:
                sec = title
            elif level >= 3:
                sub = title

        return {
            "document_title": self.doc_title,
            "chapter": ch,
            "section": sec,
            "subsection": sub,
            "hierarchy_path": " > ".join([item[1] for item in self.stack]) if self.stack else "General"
        }
