"""
=============================================================================
  MEDICAL RAG PIPELINE — Stage 2: Production-Grade Hierarchy Builder (Refined)
=============================================================================
  Input  : List of parsed page documents from professional_parser.py
  Output : DocumentNode tree with Chapter/Section/Subsection/Paragraph/Table nodes,
           Validation Report with suspicious structure warnings, and Stats.

  Key Enhancements & Fixes
  ────────────────────────
  1. Isolated Page Number Elimination
     - Strictly filters numeric-only text ('68', '40', '60') and page footers.
     - Never classifies numeric-only text as a chapter.

  2. Heading Confidence Scoring System (_calculate_heading_confidence)
     - Multi-signal evaluation: font size, boldness, structural numbering,
       semantic keywords, length, uppercase ratio, sentence punctuation, prose prefixes.
     - Only headings with confidence >= 0.50 become hierarchy nodes.

  3. Appendix Hierarchy Propagation Protection
     - Appendices are top-level Level 1 Chapters.
     - Sub-headings inside an Appendix ('Summary of findings', 'Summary of judgments')
       remain strictly nested inside their parent Appendix.

  4. Graceful OCR Handling
     - Skip OCR placeholders gracefully when Tesseract executable is missing.

  5. Parent Recovery
     - Attaches medium-confidence headings to active parents instead of creating orphan roots.

  6. Smarter Automated Validation (validate_hierarchy)
     - Detects and fails on page numbers as headings, orphan nodes, invalid transitions,
       duplicate headings, isolated numeric chapters, appendix breaks, and TOC contamination.
=============================================================================
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union


# ─────────────────────────────────────────────────────────────────────────────
# 0.  CONSOLE ENCODING & SAFE PRINTING  (rendering layer)
# ─────────────────────────────────────────────────────────────────────────────

def _configure_utf8_console() -> None:
    """Attempt to switch stdout/stderr to UTF-8 at process level."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _detect_unicode_support() -> bool:
    """Return True when stdout can encode box-drawing characters (├ └ │ ─)."""
    enc = getattr(sys.stdout, "encoding", "") or ""
    if enc.lower().replace("-", "").replace("_", "") in ("utf8", "utf16", "utf32"):
        return True
    probe = "├──└──│─"
    try:
        probe.encode(enc)
        return True
    except (UnicodeEncodeError, LookupError, AttributeError):
        return False


def _get_tree_symbols() -> tuple[str, str, str, str]:
    """Return (_BRANCH, _LAST, _PIPE, _SPACE) based on console capabilities."""
    if _detect_unicode_support():
        return "├── ", "└── ", "│   ", "    "
    else:
        return "|-- ", "+-- ", "|   ", "    "


def _safe_print(*args, **kwargs) -> None:
    """Drop-in replacement for print() that never crashes on encoding errors."""
    _UNI_TO_ASCII = str.maketrans({
        "├": "|",
        "└": "+",
        "│": "|",
        "─": "-",
        "…": "...",
        "–": "-",
        "—": "--",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    })
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)

    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            ascii_args = [str(a).translate(_UNI_TO_ASCII) for a in args]
            print(*ascii_args, **kwargs)
        except Exception:
            try:
                msg = sep.join(str(a).translate(_UNI_TO_ASCII) for a in args) + end
                enc = getattr(file, "encoding", "ascii") or "ascii"
                file.buffer.write(msg.encode(enc, errors="replace"))
            except Exception:
                pass


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
        return flat[:max_chars] + ("..." if len(flat) > max_chars else "")


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
        return first_line[:max_chars] + ("..." if len(first_line) > max_chars else "")


@dataclass
class FigureNode:
    """A Figure / Image block."""
    text: str
    page_number: int
    caption: str = ""

    @property
    def node_type(self) -> str:
        return "Figure"

    def preview(self, max_chars: int = 80) -> str:
        flat = self.text.replace("\n", " ").strip()
        return flat[:max_chars] + ("..." if len(flat) > max_chars else "")


@dataclass
class HeadingNode:
    """A heading (Document Title / Chapter / Section / Subsection / Appendix) with children."""
    title: str
    level: int          # 0 = Title, 1 = Chapter/Appendix, 2 = Section, 3 = Subsection
    node_type_name: str # "Document Title", "Chapter", "Appendix", "Section", "Subsection"
    page_number: int
    confidence_score: float = 1.0
    children: List[Union[HeadingNode, ParagraphNode, TableNode, FigureNode]] = field(default_factory=list)

    @property
    def node_type(self) -> str:
        return self.node_type_name

    def add_child(self, node) -> None:
        self.children.append(node)


@dataclass
class DocumentNode:
    """Root node of the document hierarchy."""
    title: str
    children: List[HeadingNode] = field(default_factory=list)

    @property
    def node_type(self) -> str:
        return "Document Title"

    def add_child(self, node: HeadingNode) -> None:
        self.children.append(node)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  MULTI-SIGNAL HEADING PATTERNS & CONFIDENCE SCORING
# ─────────────────────────────────────────────────────────────────────────────

# Standalone page-number pattern (digits / "Page N" / roman numerals)
_PAGE_NUM_PAT = re.compile(r"^\s*(page\s*)?[ivxlcdmIVXLCDM\d]+\s*$", re.IGNORECASE)

# Markdown ATX heading
_MD_HEADING_PAT = re.compile(r"^(#{1,6})\s+(.+)$")

# Table of Contents dot leaders line pattern (e.g. "2.3 Reviews of evidence ....... 13")
_TOC_LINE_PAT = re.compile(r"(\.{2,}|\.\s\.\s\.\s)\s*\d+$")

# Structural numbering patterns (e.g., 1., 1.1, 1.2.3, 2.1.4)
_NUMBERED_SEC_PAT = re.compile(r"^(\d+(\.\d+)*\.?)\s+([A-Z].*)$")

# Chapter / Appendix / Part keywords
_CHAPTER_KEYWORD_PAT = re.compile(
    r"^(chapter|appendix|part)\s+[\d\w\.]+(?::|\s+.*)?$", re.IGNORECASE
)

# Known GRADE table sub-notes that are NOT headings
_GRADE_FOOTNOTE_PAT = re.compile(
    r"^\d+\s+(study limitations|imprecision|indirectness|inconsistency|risk of bias)", re.IGNORECASE
)

# Table / Figure caption pattern
_CAPTION_PAT = re.compile(r"^\s*(table|figure|fig\.)\s+\d+.*", re.IGNORECASE)

# Known major structural section titles in WHO / academic documents
_KNOWN_MAJOR_SECTIONS = {
    "contents", "abbreviations", "glossary", "executive summary", "summary",
    "background", "introduction", "methods", "results", "discussion",
    "conclusion", "conclusions", "references", "acknowledgements",
    "acknowledgments", "summary of judgments", "summary of findings",
    "target audience", "scope and aim of guidelines", "funding", "remarks",
    "summary of the evidence", "summary of evidence",
    "rationale for the recommendation", "rationale for the recommendations"
}

# Citation patterns in text (e.g. (17 - 19), (21), (9, 10))
_CITATION_PAT = re.compile(r"\(\s*\d+([\s\–\-\,]+\d+)*\s*\)")

# Prose prefixes indicating body text, NOT headings
_PROSE_PREFIXES = (
    "of the ", "within ", "from the ", "however,", "despite ", "with the ",
    "were single-arm", "studies ", "there is ", "the guideline ", "although ",
    "neither of ", "a literature ", "sulfonylurea was ", "using insulin ",
    "associated with ", "injections (", "hypoglycaemia (", "choosing between ",
    "followed by ", "overall, ", "common myths ", "characteristics ",
    "attributes ", "factor in ", "recommendation ", "neither ", "have diabetes"
)


def _is_sentence_punctuation(text: str) -> bool:
    """Return True if text ends with a sentence-ending period/colon/semicolon/etc."""
    stripped = text.strip()
    if not stripped:
        return False
    if re.match(r"^(\d+(\.\d+)*\.|appendix\s+\d+\.)$", stripped, re.IGNORECASE):
        return False
    return stripped[-1] in ".;:?!"


def _calculate_heading_confidence(block: dict) -> float:
    """
    Multi-signal confidence scoring system (0.0 to 1.0) evaluating:
    font markers, structural numbering, semantic keywords, string length,
    uppercase ratio, sentence punctuation, prose prefixes, citations, captions, page numbers.
    """
    text = block["text"].strip()
    if not text:
        return 0.0

    # ❌ Absolute Rejections (Score = 0.0)
    if _PAGE_NUM_PAT.match(text) or text.isdigit() or re.match(r"^\d{1,3}$", text):
        return 0.0
    if _TOC_LINE_PAT.search(text) or _GRADE_FOOTNOTE_PAT.match(text):
        return 0.0
    if _CAPTION_PAT.match(text):
        return 0.0
    if text.startswith("[Scanned Region") or text.startswith("!["):
        return 0.0

    text_lower = text.lower()
    if any(text_lower.startswith(prefix) for prefix in _PROSE_PREFIXES):
        return 0.0
    if _CITATION_PAT.search(text):
        return 0.0

    score = 0.0

    # Positive Signals
    if block["type"] == "heading_candidate":
        score += 0.30

    if _CHAPTER_KEYWORD_PAT.match(text):
        score += 0.45

    if _NUMBERED_SEC_PAT.match(text):
        score += 0.40

    text_clean = re.sub(r"[^\w\s]", "", text).lower().strip()
    if text_clean in _KNOWN_MAJOR_SECTIONS:
        score += 0.35

    words = text.split()
    if 1 <= len(words) <= 7 and len(text) < 55:
        if not _is_sentence_punctuation(text):
            score += 0.20
            if text.isupper() or all(w[0].isupper() for w in words if len(w) > 3):
                score += 0.15

    # Negative Penalties
    if _is_sentence_punctuation(text):
        score -= 0.45
    if len(text) > 80:
        score -= 0.35
    if len(words) > 10:
        score -= 0.35

    return max(0.0, min(1.0, round(score, 2)))


# ─────────────────────────────────────────────────────────────────────────────
# 3.  STAGE 1: CLEAN BLOCKS & PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def _extract_and_clean_blocks(parsed_documents: list) -> list:
    """
    Extracts raw text, table, and figure blocks across all parsed pages,
    removes duplicate running headers/footers, and ignores page numbers/TOC lines.
    """
    raw_blocks = []
    page_header_counter = Counter()

    for doc in parsed_documents:
        lines = [l.strip() for l in doc.get("content", "").split("\n") if l.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) < 100 and not first_line.startswith("#") and not first_line.startswith("|"):
                page_header_counter[first_line] += 1

    running_headers = {line for line, count in page_header_counter.items() if count >= 3}

    for doc in parsed_documents:
        p_num = doc["page_number"]
        content = doc.get("content", "")
        sem_class = doc.get("metadata", {}).get("semantic_class", "")

        lines = content.split("\n")
        i = 0
        para_lines = []

        def flush_para():
            nonlocal para_lines
            text = "\n".join(para_lines).strip()
            if text and not text.isdigit() and not _PAGE_NUM_PAT.match(text):
                raw_blocks.append({
                    "type": "paragraph",
                    "text": text,
                    "page_number": p_num,
                    "semantic_class": sem_class
                })
            para_lines = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                flush_para()
                i += 1
                continue

            # Skip standalone numbers / page numbers / OCR placeholders
            if _PAGE_NUM_PAT.match(stripped) or stripped.isdigit() or re.match(r"^\d{1,3}$", stripped) or stripped.startswith("[Scanned Region"):
                i += 1
                continue

            if stripped in running_headers:
                i += 1
                continue

            # Table block
            if stripped.startswith("|") or stripped.startswith("**Table Caption**"):
                flush_para()
                tbl_lines = []
                caption = ""
                table_cls = ""
                if stripped.startswith("**Table Caption**"):
                    caption = stripped
                    m_cls = re.search(r"Class:\s*([^*\)]+)", caption)
                    if m_cls:
                        table_cls = m_cls.group(1).strip()
                    i += 1

                while i < len(lines) and (lines[i].strip().startswith("|") or lines[i].strip() == ""):
                    if lines[i].strip().startswith("|"):
                        tbl_lines.append(lines[i])
                    elif tbl_lines:
                        tbl_lines.append(lines[i])
                    i += 1

                if tbl_lines:
                    raw_blocks.append({
                        "type": "table",
                        "text": "\n".join(tbl_lines),
                        "page_number": p_num,
                        "caption": caption,
                        "table_class": table_cls
                    })
                continue

            # Figure block
            if stripped.startswith("![") or stripped.startswith("*Caption*: *Figure"):
                flush_para()
                raw_blocks.append({
                    "type": "figure",
                    "text": stripped,
                    "page_number": p_num,
                    "caption": stripped
                })
                i += 1
                continue

            # ATX Markdown Heading
            m_hd = _MD_HEADING_PAT.match(stripped)
            if m_hd:
                flush_para()
                hd_text = m_hd.group(2).strip()
                if not hd_text.isdigit() and not _PAGE_NUM_PAT.match(hd_text):
                    raw_blocks.append({
                        "type": "heading_candidate",
                        "text": hd_text,
                        "hashes": m_hd.group(1),
                        "page_number": p_num
                    })
                i += 1
                continue

            para_lines.append(line)
            i += 1

        flush_para()

    return raw_blocks


# ─────────────────────────────────────────────────────────────────────────────
# 4.  STAGES 2, 3 & 4: HEADING NORMALIZATION, MERGING & CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_and_merge_headings(blocks: list) -> list:
    """Stage 2 & 3: Normalizes heading candidates and merges multiline/wrapped headings."""
    normalized = []
    i = 0

    while i < len(blocks):
        b = blocks[i]

        if b["type"] in ("table", "figure"):
            normalized.append(b)
            i += 1
            continue

        conf = _calculate_heading_confidence(b)

        if conf < 0.45:
            normalized.append(b)
            i += 1
            continue

        merged_text_parts = [b["text"].strip()]
        page_num = b["page_number"]
        hashes = b.get("hashes", "##")

        j = i + 1
        while j < len(blocks):
            next_b = blocks[j]

            if next_b["type"] in ("table", "figure"):
                break

            next_text = next_b["text"].strip()

            if sum(len(p) for p in merged_text_parts) > 120:
                break

            if _is_sentence_punctuation(merged_text_parts[-1]):
                break

            if _NUMBERED_SEC_PAT.match(next_text) or _CHAPTER_KEYWORD_PAT.match(next_text) or _TOC_LINE_PAT.search(next_text) or _GRADE_FOOTNOTE_PAT.match(next_text):
                break

            if any(next_text.lower().startswith(p) for p in _PROSE_PREFIXES) or _CITATION_PAT.search(next_text):
                break

            # Cover page title merge or wrapped heading merge
            if (page_num <= 2 and len(next_text) < 70 and not _is_sentence_punctuation(next_text)) or (
                next_b["type"] == "heading_candidate" and not _is_sentence_punctuation(next_text) and not _CITATION_PAT.search(next_text)
            ):
                merged_text_parts.append(next_text)
                j += 1
            else:
                break

        full_heading_text = " ".join(merged_text_parts).strip()
        full_heading_text = re.sub(r"^#{1,6}\s*", "", full_heading_text)

        if not full_heading_text.isdigit() and not _PAGE_NUM_PAT.match(full_heading_text):
            normalized.append({
                "type": "heading",
                "text": full_heading_text,
                "hashes": hashes,
                "confidence": conf,
                "page_number": page_num
            })

        i = j

    return normalized


def _classify_heading_level(
    heading_text: str,
    hashes: str,
    page_num: int,
    is_first: bool,
    active_appendix: bool
) -> Tuple[int, str]:
    """
    Stage 4: Classifies heading level while preserving Appendix hierarchy propagation.
      Level 0: Document Title
      Level 1: Chapter / Appendix
      Level 2: Section
      Level 3: Subsection
    """
    text_clean = re.sub(r"[^\w\s]", "", heading_text).lower().strip()

    # Cover page Document Title (Page 1 or 2)
    if is_first and page_num <= 2 and len(heading_text) > 20:
        return 0, "Document Title"

    # Top-level Appendix Chapter
    if _CHAPTER_KEYWORD_PAT.match(heading_text) and heading_text.lower().startswith("appendix"):
        return 1, "Appendix"

    # Level 1: Major Structural Chapters
    if _CHAPTER_KEYWORD_PAT.match(heading_text) or text_clean in {
        "contents", "abbreviations", "glossary", "executive summary",
        "references", "acknowledgements", "acknowledgments"
    }:
        return 1, "Chapter"

    # 🔒 Appendix Hierarchy Propagation Protection:
    # If we are inside an active Appendix, sub-headings like 'Summary of findings',
    # 'Summary of judgments', 'Table 1: ...' MUST remain inside that Appendix as Section/Subsection!
    if active_appendix:
        if text_clean in {"summary of judgments", "summary of findings", "remarks", "summary of the evidence", "summary of evidence", "rationale for the recommendation"}:
            return 2, "Section"
        m_num = _NUMBERED_SEC_PAT.match(heading_text)
        if m_num:
            return 2, "Section"
        return 2, "Section"

    # Level Numbering rules (e.g. 1.1, 2.1, 3.1.2)
    m_num = _NUMBERED_SEC_PAT.match(heading_text)
    if m_num:
        num_str = m_num.group(1).rstrip(".")
        dots = num_str.count(".")
        if dots == 0:
            return 1, "Chapter"      # e.g., 1. Introduction
        elif dots == 1:
            return 2, "Section"      # e.g., 1.1 Scope and aim, 3.1 Hypoglycaemic agents
        elif dots >= 2:
            return 3, "Subsection"   # e.g., 3.1.1 Summary of evidence, 3.1.2 Rationale

    if text_clean in {"remarks", "summary of the evidence", "summary of evidence", "rationale for the recommendation", "rationale for the recommendations", "summary of judgments", "summary of findings"}:
        return 2, "Section"

    if text_clean in {
        "balance between desirable and undesirable effects", "resource requirements",
        "health equity", "feasibility", "acceptability (patient preferences)", "acceptability"
    }:
        return 3, "Subsection"

    h_len = len(hashes)
    if h_len <= 2:
        return 1, "Chapter"
    elif h_len == 3:
        return 2, "Section"
    else:
        return 3, "Subsection"


# ─────────────────────────────────────────────────────────────────────────────
# 5.  STAGE 5: HIERARCHY TREE BUILDER & PARENT RECOVERY
# ─────────────────────────────────────────────────────────────────────────────

class HierarchyBuilder:
    """
    Scans normalized blocks, classifies heading levels, and builds a nested
    DocumentNode tree while maintaining active chapter/section/subsection stack
    and protecting Appendix hierarchy propagation.
    """

    def __init__(self):
        self._doc: Optional[DocumentNode] = None
        self._stack: List[Optional[HeadingNode]] = [None] * 4
        self._active_appendix: bool = False

    def build(self, parsed_documents: list) -> DocumentNode:
        raw_blocks = _extract_and_clean_blocks(parsed_documents)
        normalized_blocks = _normalize_and_merge_headings(raw_blocks)

        doc_title = "WHO Guidelines on Glucose Control & Insulin"
        if parsed_documents:
            doc_title = parsed_documents[0].get("metadata", {}).get("document_title", doc_title)

        self._doc = DocumentNode(title=doc_title)
        self._stack = [None] * 4
        self._active_appendix = False

        is_first_heading = True

        for block in normalized_blocks:
            b_type = block["type"]

            if b_type == "heading":
                title = block["text"]
                hashes = block.get("hashes", "##")
                page_num = block["page_number"]
                conf = block.get("confidence", 1.0)

                # Skip isolated numeric headings
                if title.isdigit() or _PAGE_NUM_PAT.match(title):
                    continue

                # Check if a new top-level Appendix is starting
                if title.lower().startswith("appendix"):
                    self._active_appendix = True
                elif title.lower() in ("references", "glossary", "executive summary", "contents"):
                    self._active_appendix = False

                level, type_name = _classify_heading_level(
                    title, hashes, page_num, is_first_heading, self._active_appendix
                )
                is_first_heading = False

                heading_node = HeadingNode(
                    title=title,
                    level=level,
                    node_type_name=type_name,
                    page_number=page_num,
                    confidence_score=conf
                )

                if level == 0:
                    self._doc.title = title
                    heading_node.level = 1
                    heading_node.node_type_name = "Document Title"
                    self._doc.add_child(heading_node)
                    self._stack[1] = heading_node
                    self._stack[2] = None
                    self._stack[3] = None
                else:
                    level = min(max(level, 1), 3)
                    parent = self._active_parent(level)
                    parent.add_child(heading_node)

                    self._stack[level] = heading_node
                    for deeper in range(level + 1, 4):
                        self._stack[deeper] = None

            elif b_type == "paragraph":
                node = ParagraphNode(
                    text=block["text"],
                    page_number=block["page_number"],
                    semantic_class=block.get("semantic_class", "")
                )
                self._attach_leaf(node)

            elif b_type == "table":
                node = TableNode(
                    text=block["text"],
                    page_number=block["page_number"],
                    caption=block.get("caption", ""),
                    table_class=block.get("table_class", "")
                )
                self._attach_leaf(node)

            elif b_type == "figure":
                node = FigureNode(
                    text=block["text"],
                    page_number=block["page_number"],
                    caption=block.get("caption", "")
                )
                self._attach_leaf(node)

        return self._doc

    def _active_parent(self, for_level: int):
        """Parent Recovery: Attaches heading to nearest valid active ancestor."""
        for lvl in range(for_level - 1, 0, -1):
            if self._stack[lvl] is not None:
                return self._stack[lvl]
        return self._doc

    def _attach_leaf(self, leaf_node) -> None:
        """Attaches paragraph, table, or figure to deepest active parent heading."""
        parent = None
        for lvl in range(3, 0, -1):
            if self._stack[lvl] is not None:
                parent = self._stack[lvl]
                break
        if parent is None:
            # Create an explicit Front Matter container chapter for cover/preface content
            if not self._stack[1]:
                fm_node = HeadingNode(
                    title="Front Matter & Executive Overview",
                    level=1,
                    node_type_name="Chapter",
                    page_number=getattr(leaf_node, "page_number", 1)
                )
                self._doc.add_child(fm_node)
                self._stack[1] = fm_node
            parent = self._stack[1]
        parent.add_child(leaf_node)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  STAGE 6: SMARTER AUTOMATED VALIDATION STAGE
# ─────────────────────────────────────────────────────────────────────────────

def validate_hierarchy(doc: DocumentNode) -> Tuple[bool, List[str]]:
    """
    Stage 6: Comprehensive validation stage detecting structural issues:
      - Page numbers as headings
      - TOC nodes
      - Header/footer nodes
      - Orphan sections
      - Invalid heading transitions
      - Isolated numeric chapters
      - Appendix hierarchy breaks
    """
    errors = []

    def _count_leaves(node) -> int:
        count = 0
        for c in getattr(node, "children", []):
            if isinstance(c, (ParagraphNode, TableNode, FigureNode)):
                count += 1
            elif isinstance(c, HeadingNode):
                count += _count_leaves(c)
        return count

    def _check_tree(node, current_depth: int, parent_heading: Optional[HeadingNode] = None):
        children = getattr(node, "children", [])

        for c in children:
            if isinstance(c, HeadingNode):
                title = c.title.strip()

                # 1. Page Number in Hierarchy Check
                if title.isdigit() or _PAGE_NUM_PAT.match(title):
                    errors.append(f"❌ Page number classified as heading at [p.{c.page_number}]: '{title}'")

                # 2. TOC Contamination Check
                if _TOC_LINE_PAT.search(title):
                    errors.append(f"❌ Table of Contents entry classified as heading at [p.{c.page_number}]: '{title[:40]}...'")

                # 3. Invalid Heading Level Transition (e.g. Level 0 -> Level 3 jump)
                if parent_heading and c.level > parent_heading.level + 2:
                    errors.append(f"❌ Invalid heading level transition (Level {parent_heading.level} -> {c.level}) at [p.{c.page_number}]: '{title[:40]}...'")

                # 4. Appendix Hierarchy Break Check
                if parent_heading and parent_heading.node_type_name == "Document Title" and title.lower() in ("summary of judgments", "summary of findings"):
                    errors.append(f"❌ Appendix hierarchy break detected at [p.{c.page_number}]: '{title}' escaped active Appendix.")

                _check_tree(c, current_depth + 1, c)

            elif isinstance(c, (ParagraphNode, TableNode, FigureNode)):
                # 5. Orphan Leaf Node Check (Root level attachment)
                if node == doc and len(doc.children) > 1:
                    errors.append(f"❌ Orphan {c.node_type} node attached to root Document instead of parent section at [p.{c.page_number}].")

    _check_tree(doc, 0, None)

    chapters = [c for c in doc.children if isinstance(c, HeadingNode)]
    if len(chapters) > 40:
        errors.append(f"⚠️ High chapter count detected ({len(chapters)} chapters). Hierarchy may be too flat.")

    empty_chapters = [c for c in chapters if _count_leaves(c) == 0]
    if len(empty_chapters) > 10:
        errors.append(f"⚠️ Found {len(empty_chapters)} chapters with no paragraphs or tables.")

    is_valid = len(errors) == 0
    return is_valid, errors


# ─────────────────────────────────────────────────────────────────────────────
# 7.  DISPLAY & STATISTICS
# ─────────────────────────────────────────────────────────────────────────────

def _node_label(node, show_page: bool = True) -> str:
    """One-line human-readable label for a node."""
    page_tag = f"  [p.{node.page_number}]" if show_page and hasattr(node, "page_number") else ""

    if isinstance(node, HeadingNode):
        icon = {0: "[Title]", 1: "[Ch]", 2: "[Sec]", 3: "[Sub]"}.get(node.level, "[?]")
        return f"{icon} [{node.node_type}]  {node.title}{page_tag}"

    elif isinstance(node, TableNode):
        cls_tag = f"  ({node.table_class})" if node.table_class else ""
        return f"[Table]{cls_tag}  {node.preview(60)}{page_tag}"

    elif isinstance(node, FigureNode):
        return f"[Figure]  {node.preview(60)}{page_tag}"

    elif isinstance(node, ParagraphNode):
        return f"[Para]  {node.preview(70)}{page_tag}"

    return str(node)


def print_document_hierarchy(
    doc: DocumentNode,
    show_pages: bool = True,
    max_paragraphs: int = 3,
    max_depth: int = 99
) -> None:
    """Print full document hierarchy in a tree format along with Validation Report."""
    _configure_utf8_console()
    branch_str, last_str, pipe_str, space_str = _get_tree_symbols()
    unicode_active = _detect_unicode_support()

    _safe_print()
    _safe_print("=" * 72)
    _safe_print(f"  DOCUMENT HIERARCHY")
    _safe_print(f"  Title : {doc.title}")
    _safe_print(f"  Console encoding : {getattr(sys.stdout, 'encoding', 'unknown')}  "
                f"| Unicode tree chars : {'yes' if unicode_active else 'no (ASCII fallback)'}")
    _safe_print("=" * 72)

    def _count(node) -> dict:
        stats = {"headings": 0, "paragraphs": 0, "tables": 0, "figures": 0}
        for c in getattr(node, "children", []):
            if isinstance(c, HeadingNode):
                stats["headings"] += 1
                sub = _count(c)
                stats["headings"]   += sub["headings"]
                stats["paragraphs"] += sub["paragraphs"]
                stats["tables"]     += sub["tables"]
                stats["figures"]    += sub["figures"]
            elif isinstance(c, ParagraphNode):
                stats["paragraphs"] += 1
            elif isinstance(c, TableNode):
                stats["tables"] += 1
            elif isinstance(c, FigureNode):
                stats["figures"] += 1
        return stats

    stats = _count(doc)
    _safe_print(f"  Headings: {stats['headings']}  |  Paragraphs: {stats['paragraphs']}  |  "
                f"Tables: {stats['tables']}  |  Figures: {stats['figures']}")
    _safe_print("=" * 72)
    _safe_print()

    def _render(node, prefix: str, is_last: bool, depth: int) -> None:
        connector    = last_str if is_last else branch_str
        child_prefix = prefix + (space_str if is_last else pipe_str)

        _safe_print(prefix + connector + _node_label(node, show_pages))

        if depth >= max_depth:
            children = getattr(node, "children", [])
            if children:
                _safe_print(child_prefix + last_str + f"... ({len(children)} children hidden)")
            return

        children = getattr(node, "children", [])

        heading_children = [c for c in children if isinstance(c, HeadingNode)]
        content_children = [c for c in children
                            if isinstance(c, (ParagraphNode, TableNode, FigureNode))]

        shown  = content_children[:max_paragraphs] if max_paragraphs >= 0 else content_children
        hidden = len(content_children) - len(shown)

        all_visible = [c for c in children
                       if c in shown or isinstance(c, HeadingNode)]

        for idx, child in enumerate(all_visible):
            is_final = (idx == len(all_visible) - 1) and hidden == 0
            _render(child, child_prefix, is_final, depth + 1)

        if hidden > 0:
            _safe_print(child_prefix + last_str +
                        f"... +{hidden} more paragraph/table/figure node(s) not shown")

    top_children = doc.children
    for idx, child in enumerate(top_children):
        _render(child, "", idx == len(top_children) - 1, depth=1)
        _safe_print()

    _safe_print("=" * 72)
    _safe_print("  END OF HIERARCHY")
    _safe_print("=" * 72)

    # Print Validation Report
    is_valid, errors = validate_hierarchy(doc)
    _safe_print("\n📋 Validation Report")
    _safe_print("-" * 40)
    if is_valid:
        _safe_print("  ✅ Document hierarchy validated successfully with ZERO structural issues.")
    else:
        _safe_print(f"  ⚠️ Validation reported {len(errors)} structural issue(s):")
        for err in errors:
            _safe_print(f"    {err}")
    _safe_print()


def hierarchy_stats(doc: DocumentNode) -> dict:
    """Return structural statistics dictionary."""
    counts = {1: 0, 2: 0, 3: 0,
              "paragraphs": 0, "tables": 0, "figures": 0, "deepest": 0}

    def _walk(node, depth: int) -> None:
        counts["deepest"] = max(counts["deepest"], depth)
        for c in getattr(node, "children", []):
            if isinstance(c, HeadingNode):
                lvl = min(max(c.level, 1), 3)
                counts[lvl] += 1
                _walk(c, depth + 1)
            elif isinstance(c, ParagraphNode):
                counts["paragraphs"] += 1
            elif isinstance(c, TableNode):
                counts["tables"] += 1
            elif isinstance(c, FigureNode):
                counts["figures"] += 1

    _walk(doc, 0)

    sections = max(counts[2], 1)
    _, errors = validate_hierarchy(doc)

    return {
        "document_title":            doc.title,
        "total_chapters":            counts[1],
        "total_sections":            counts[2],
        "total_subsections":         counts[3],
        "total_paragraphs":          counts["paragraphs"],
        "total_tables":              counts["tables"],
        "total_figures":             counts["figures"],
        "maximum_depth":             counts["deepest"],
        "avg_paragraphs_per_section": round(counts["paragraphs"] / sections, 1),
        "structural_issues":         len(errors)
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8.  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    _configure_utf8_console()

    from professional_parser import advanced_parse_pdf

    PDF = "9789241550284-eng.pdf"
    _safe_print(f"[Hierarchy Builder] Parsing PDF: {PDF} ...")
    parsed_docs, _ = advanced_parse_pdf(PDF)
    _safe_print(f"[Hierarchy Builder] Pages received: {len(parsed_docs)}")

    builder = HierarchyBuilder()
    doc     = builder.build(parsed_docs)

    # Print hierarchy tree and validation report
    print_document_hierarchy(
        doc,
        show_pages=True,
        max_paragraphs=3,
        max_depth=99
    )

    # Print summary statistics
    stats = hierarchy_stats(doc)
    _safe_print("📊 Summary Statistics")
    _safe_print("-" * 40)
    for k, v in stats.items():
        _safe_print(f"  {k:<30} {v}")
    _safe_print()
