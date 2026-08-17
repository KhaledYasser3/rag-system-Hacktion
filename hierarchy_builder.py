"""
=============================================================================
  MEDICAL RAG PIPELINE — Stage 2: Hierarchy Builder
=============================================================================
  Input  : List of parsed page documents from professional_parser.py
  Output : DocumentHierarchy object — a tree of Chapter/Section/Paragraph nodes

  What this module does
  ─────────────────────
  1. Scans every parsed page in order (no merging, no chunking).
  2. Detects headings by reading Markdown markers produced by the parser:
       #       → document title  (level 0)
       ##      → chapter         (level 1)
       ###     → chapter         (level 1, alternative)
       ####    → section         (level 2)
       #####   → subsection      (level 3)
       ######  → sub-subsection  (level 4)
     Plain lines that are short, title-cased, and end without punctuation
     are also treated as implicit section headings (heuristic fallback).
  3. Paragraphs and table blocks are attached to the deepest active heading.
  4. Page numbers are NOT stored as hierarchy nodes.
  5. The result can be inspected with print_document_hierarchy().

  Node Types
  ──────────
  DocumentNode  – root of the tree
  HeadingNode   – chapter / section / subsection
  ParagraphNode – a block of body text
  TableNode     – a Markdown table block (kept atomic)
=============================================================================
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# 1.  DATA MODEL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParagraphNode:
    """A body-text block attached to the nearest heading."""
    text: str
    page_number: int
    semantic_class: str = ""

    @property
    def node_type(self) -> str:
        return "Paragraph"

    def preview(self, max_chars: int = 80) -> str:
        flat = self.text.replace("\n", " ").strip()
        return flat[:max_chars] + ("…" if len(flat) > max_chars else "")


@dataclass
class TableNode:
    """A Markdown table block kept as an atomic unit."""
    text: str
    page_number: int
    caption: str = ""
    table_class: str = ""

    @property
    def node_type(self) -> str:
        return "Table"

    def preview(self, max_chars: int = 80) -> str:
        first_line = self.text.strip().split("\n")[0]
        return first_line[:max_chars] + ("…" if len(first_line) > max_chars else "")


@dataclass
class HeadingNode:
    """A heading (chapter / section / subsection) with its child nodes."""
    title: str
    level: int          # 1 = chapter, 2 = section, 3 = subsection, 4 = sub-subsection
    page_number: int
    children: List = field(default_factory=list)   # HeadingNode | ParagraphNode | TableNode

    @property
    def node_type(self) -> str:
        labels = {1: "Chapter", 2: "Section", 3: "Subsection", 4: "Sub-Subsection"}
        return labels.get(self.level, f"Level-{self.level}")

    def add_child(self, node) -> None:
        self.children.append(node)


@dataclass
class DocumentNode:
    """Root of the entire document hierarchy."""
    title: str
    children: List[HeadingNode] = field(default_factory=list)

    @property
    def node_type(self) -> str:
        return "Document"

    def add_child(self, node: HeadingNode) -> None:
        self.children.append(node)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  HEADING DETECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# Regex that matches Markdown ATX headings: "## Some Title"
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")

# Page-number-only line: just digits / "Page N" / roman numerals / short standalone numbers
_PAGE_NUM   = re.compile(
    r"^\s*(page\s*)?[ivxlcdmIVXLCDM\d]+\s*$",
    re.IGNORECASE
)

# Markdown table row / separator line
_TABLE_ROW  = re.compile(r"^\|")

# Bold caption e.g. "**Table Caption**: ..."
_CAPTION    = re.compile(r"^\*\*Table Caption\*\*", re.IGNORECASE)


def _md_heading_level(hashes: str) -> int:
    """Map '#' count to hierarchy level (clamped to 1-4)."""
    n = len(hashes)
    if n <= 2:   return 1   # # or ## → Chapter
    elif n == 3: return 1   # ### still treated as chapter in WHO doc
    elif n == 4: return 2   # #### → Section
    elif n == 5: return 3   # ##### → Subsection
    else:        return 4   # ###### → Sub-Subsection


def _is_implicit_heading(line: str) -> bool:
    """
    Disabled. The parser already marks every real heading with Markdown
    ATX syntax (##, ####, etc.). Plain-text lines are always paragraphs.
    """
    return False




# ─────────────────────────────────────────────────────────────────────────────
# 3.  LINE-LEVEL PARSER  (runs on the content of a single page)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_page_into_blocks(content: str, page_number: int, semantic_class: str):
    """
    Split one page's Markdown content into an ordered list of node objects:
      HeadingNode | ParagraphNode | TableNode

    Tables are consumed as contiguous |…| blocks.
    Paragraphs are collected by blank-line separation.
    """
    blocks = []
    lines  = content.split("\n")

    i = 0
    para_lines: List[str] = []
    caption_buf: str = ""

    def flush_para():
        nonlocal para_lines
        text = "\n".join(para_lines).strip()
        if text:
            blocks.append(ParagraphNode(
                text=text,
                page_number=page_number,
                semantic_class=semantic_class
            ))
        para_lines = []

    while i < len(lines):
        line = lines[i]
        raw  = line.rstrip()

        # ── Skip page-number-only lines ──────────────────────────────────────
        if _PAGE_NUM.match(raw):
            i += 1
            continue

        # ── Markdown ATX heading ─────────────────────────────────────────────
        m = _MD_HEADING.match(raw)
        if m:
            flush_para()
            hashes, title = m.group(1), m.group(2).strip()
            # Skip if the heading text is itself just a page number
            if _PAGE_NUM.match(title):
                i += 1
                continue
            # Sanity guard 1: real headings are short.
            # Lines > 120 chars are mis-tagged body sentences.
            if len(title) > 120:
                para_lines.append(title)
                i += 1
                continue
            # Sanity guard 2: real headings do NOT end with sentence punctuation.
            # Body sentences mis-tagged with ### by the XY-Cut parser do.
            if title.rstrip()[-1] in ".;,)":
                para_lines.append(title)
                i += 1
                continue
            level = _md_heading_level(hashes)
            blocks.append(HeadingNode(title=title, level=level, page_number=page_number))
            i += 1
            continue

        # ── Table caption line ───────────────────────────────────────────────
        if _CAPTION.match(raw):
            caption_buf = raw
            i += 1
            continue

        # ── Table block (consume until no more | lines) ──────────────────────
        if _TABLE_ROW.match(raw):
            flush_para()
            table_lines = []
            table_class = ""
            # Detect class from caption buffer
            if caption_buf:
                m_cls = re.search(r"Class:\s*([^*\)]+)", caption_buf)
                table_class = m_cls.group(1).strip() if m_cls else ""

            while i < len(lines) and (_TABLE_ROW.match(lines[i]) or lines[i].strip() == ""):
                if _TABLE_ROW.match(lines[i]):
                    table_lines.append(lines[i])
                elif table_lines:            # allow one blank line inside table
                    table_lines.append(lines[i])
                i += 1

            blocks.append(TableNode(
                text="\n".join(table_lines),
                page_number=page_number,
                caption=caption_buf,
                table_class=table_class
            ))
            caption_buf = ""
            continue

        # ── Blank line → flush current paragraph ────────────────────────────
        if raw.strip() == "":
            flush_para()
            i += 1
            continue

        # ── Implicit heading heuristic ───────────────────────────────────────
        if _is_implicit_heading(raw) and not para_lines:
            flush_para()
            blocks.append(HeadingNode(title=raw.strip(), level=2, page_number=page_number))
            i += 1
            continue

        # ── Normal text line ─────────────────────────────────────────────────
        para_lines.append(raw)
        i += 1

    flush_para()
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# 4.  HIERARCHY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

class HierarchyBuilder:
    """
    Scans all parsed pages and builds a DocumentNode tree.

    Active-heading stack:
      stack[0] = document root   (level 0)
      stack[1] = active chapter  (level 1)
      stack[2] = active section  (level 2)
      stack[3] = active subsect. (level 3)
      stack[4] = sub-subsection  (level 4)
    """

    def __init__(self):
        self._doc: Optional[DocumentNode] = None
        # stack[level] holds the currently active HeadingNode at that level
        self._stack: List[Optional[HeadingNode]] = [None] * 5

    # ── Public API ───────────────────────────────────────────────────────────

    def build(self, parsed_documents: list) -> DocumentNode:
        """
        Main entry point.

        Parameters
        ----------
        parsed_documents : list
            Output of ``advanced_parse_pdf()`` — a list of dicts with keys
            ``page_number``, ``content``, ``metadata``.

        Returns
        -------
        DocumentNode
            Root of the complete document hierarchy.
        """
        # Derive document title from first page metadata
        title = "Unknown Document"
        if parsed_documents:
            title = (parsed_documents[0]
                     .get("metadata", {})
                     .get("document_title", "Unknown Document"))

        self._doc = DocumentNode(title=title)
        self._stack = [None] * 5

        for page_doc in parsed_documents:
            page_num      = page_doc["page_number"]
            content       = page_doc.get("content", "")
            sem_class     = page_doc.get("metadata", {}).get("semantic_class", "")

            blocks = _parse_page_into_blocks(content, page_num, sem_class)

            for block in blocks:
                self._insert(block)

        return self._doc

    # ── Private helpers ──────────────────────────────────────────────────────

    def _active_parent(self, for_level: int):
        """
        Return the nearest active ancestor for a node that belongs at `for_level`.
        Falls back to the document root if no heading is active.
        """
        # For a heading at `for_level`, its parent is the last active heading
        # at level < for_level.
        for lvl in range(for_level - 1, 0, -1):
            if self._stack[lvl] is not None:
                return self._stack[lvl]
        return self._doc    # top-level, attach to document root

    def _insert(self, block) -> None:
        if isinstance(block, HeadingNode):
            level = min(block.level, 4)
            parent = self._active_parent(level)
            parent.add_child(block)
            # Update stack: set this level, clear all deeper levels
            self._stack[level] = block
            for deeper in range(level + 1, 5):
                self._stack[deeper] = None

        elif isinstance(block, (ParagraphNode, TableNode)):
            # Attach to the deepest active heading
            parent = None
            for lvl in range(4, 0, -1):
                if self._stack[lvl] is not None:
                    parent = self._stack[lvl]
                    break
            if parent is None:
                parent = self._doc
            parent.add_child(block)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  DEBUG PRINTER
# ─────────────────────────────────────────────────────────────────────────────

# Tree drawing characters
_BRANCH = "├── "
_LAST   = "└── "
_PIPE   = "│    "
_SPACE  = "     "


def _node_label(node, show_page: bool = True) -> str:
    """One-line human-readable label for a node."""
    page_tag = f"  [p.{node.page_number}]" if show_page and hasattr(node, "page_number") else ""

    if isinstance(node, HeadingNode):
        icon = {1: "[Ch]", 2: "[Sec]", 3: "[Sub]", 4: "[SSub]"}.get(node.level, "[?]")
        return f"{icon} [{node.node_type}]  {node.title}{page_tag}"

    elif isinstance(node, TableNode):
        cls_tag = f"  ({node.table_class})" if node.table_class else ""
        return f"[Table]{cls_tag}  {node.preview(60)}{page_tag}"

    elif isinstance(node, ParagraphNode):
        return f"[Para]  {node.preview(70)}{page_tag}"

    return str(node)


def _print_tree(node, prefix: str = "", is_last: bool = True, show_page: bool = True) -> None:
    connector = _LAST if is_last else _BRANCH
    print(prefix + connector + _node_label(node, show_page))
    child_prefix = prefix + (_SPACE if is_last else _PIPE)

    children = getattr(node, "children", [])
    for idx, child in enumerate(children):
        _print_tree(child, child_prefix, idx == len(children) - 1, show_page)


def print_document_hierarchy(
    doc: DocumentNode,
    show_pages: bool = True,
    max_paragraphs: int = 3,
    max_depth: int = 99
) -> None:
    """
    Print the full document hierarchy in a tree format.

    Parameters
    ----------
    doc : DocumentNode
        The root returned by HierarchyBuilder.build().
    show_pages : bool
        Whether to print [p.N] page annotations (default True).
    max_paragraphs : int
        Max paragraph/table nodes to print per heading before collapsing.
        Set to 0 to hide all paragraphs; set to 999 to show all.
    max_depth : int
        Stop printing children beyond this depth (0 = root only).
    """

    print()
    print("=" * 72)
    print(f"  DOCUMENT HIERARCHY")
    print(f"  Title : {doc.title}")
    print("=" * 72)

    def _count(node) -> dict:
        """Quick stats: total headings, paragraphs, tables."""
        stats = {"headings": 0, "paragraphs": 0, "tables": 0}
        for c in getattr(node, "children", []):
            if isinstance(c, HeadingNode):
                stats["headings"] += 1
                sub = _count(c)
                stats["headings"]   += sub["headings"]
                stats["paragraphs"] += sub["paragraphs"]
                stats["tables"]     += sub["tables"]
            elif isinstance(c, ParagraphNode):
                stats["paragraphs"] += 1
            elif isinstance(c, TableNode):
                stats["tables"] += 1
        return stats

    stats = _count(doc)
    print(f"  Headings: {stats['headings']}  |  Paragraphs: {stats['paragraphs']}  |  Tables: {stats['tables']}")
    print("=" * 72)
    print()

    def _render(node, prefix: str, is_last: bool, depth: int) -> None:
        connector    = _LAST if is_last else _BRANCH
        child_prefix = prefix + (_SPACE if is_last else _PIPE)

        print(prefix + connector + _node_label(node, show_pages))

        if depth >= max_depth:
            children = getattr(node, "children", [])
            if children:
                print(child_prefix + _LAST + f"… ({len(children)} children hidden)")
            return

        children = getattr(node, "children", [])

        # Separate structural headings from leaf content nodes
        heading_children = [c for c in children if isinstance(c, HeadingNode)]
        content_children = [c for c in children
                            if isinstance(c, (ParagraphNode, TableNode))]

        # Show limited content nodes
        shown   = content_children[:max_paragraphs] if max_paragraphs >= 0 else content_children
        hidden  = len(content_children) - len(shown)
        all_vis = shown + heading_children
        # Re-interleave to preserve original order
        all_visible = [c for c in children
                       if c in shown or isinstance(c, HeadingNode)]

        for idx, child in enumerate(all_visible):
            is_final = (idx == len(all_visible) - 1) and hidden == 0
            _render(child, child_prefix, is_final, depth + 1)

        if hidden > 0:
            print(child_prefix + _LAST +
                  f"… +{hidden} more paragraph/table node(s) not shown")

    # Print each top-level child of the document
    top_children = doc.children
    for idx, child in enumerate(top_children):
        _render(child, "", idx == len(top_children) - 1, depth=1)
        print()

    print("=" * 72)
    print("  END OF HIERARCHY")
    print("=" * 72)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# 6.  STATISTICS HELPER
# ─────────────────────────────────────────────────────────────────────────────

def hierarchy_stats(doc: DocumentNode) -> dict:
    """
    Return a flat statistics dictionary about the hierarchy.

    Keys
    ────
    total_chapters, total_sections, total_subsections,
    total_paragraphs, total_tables,
    avg_paragraphs_per_section, deepest_level
    """
    counts = {1: 0, 2: 0, 3: 0, 4: 0,
              "paragraphs": 0, "tables": 0, "deepest": 0}

    def _walk(node, depth: int) -> None:
        counts["deepest"] = max(counts["deepest"], depth)
        for c in getattr(node, "children", []):
            if isinstance(c, HeadingNode):
                lvl = min(c.level, 4)
                counts[lvl] += 1
                _walk(c, depth + 1)
            elif isinstance(c, ParagraphNode):
                counts["paragraphs"] += 1
            elif isinstance(c, TableNode):
                counts["tables"] += 1

    _walk(doc, 0)

    sections = max(counts[2], 1)
    return {
        "total_chapters":            counts[1],
        "total_sections":            counts[2],
        "total_subsections":         counts[3],
        "total_sub_subsections":     counts[4],
        "total_paragraphs":          counts["paragraphs"],
        "total_tables":              counts["tables"],
        "avg_paragraphs_per_section": round(counts["paragraphs"] / sections, 1),
        "deepest_level":             counts["deepest"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7.  ENTRY POINT  (run this file directly to inspect the hierarchy)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    from professional_parser import advanced_parse_pdf

    PDF = "9789241550284-eng.pdf"
    print(f"[Hierarchy Builder] Parsing PDF: {PDF} …")
    parsed_docs, _ = advanced_parse_pdf(PDF)
    print(f"[Hierarchy Builder] Pages received: {len(parsed_docs)}")

    builder = HierarchyBuilder()
    doc     = builder.build(parsed_docs)

    # ── Print hierarchy (show first 3 paragraphs per heading, all depths) ──
    print_document_hierarchy(
        doc,
        show_pages=True,
        max_paragraphs=3,
        max_depth=99
    )

    # ── Print statistics ────────────────────────────────────────────────────
    stats = hierarchy_stats(doc)
    print("\nHierarchy Statistics")
    print("─" * 40)
    for k, v in stats.items():
        print(f"  {k:<35} {v}")
    print()
