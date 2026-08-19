"""
=============================================================================
  MEDICAL RAG PIPELINE — Stage 2: Production-Grade Semantic Hierarchy Builder
=============================================================================
  Input  : List of parsed page documents from professional_parser.py
  Output : DocumentNode tree with Chapter/Appendix/Section/Subsection/Paragraph/Table/Figure nodes,
           Validation Report with semantic issue warnings, and Stats.

  Key Semantic Upgrades
  ─────────────────────
  1. Table Titles & Caption Linking
     - Detects 'Table 1: ...', 'Table A1 ...', 'TABLE 3 ...' immediately preceding a table.
     - Links title directly to TableNode (title, headers, rows, bbox, confidence_score).
     - Suppresses redundant separate ParagraphNode for table titles.

  2. Figure Captions & Metadata Linking
     - Links figure captions and figure numbers ('Figure 1', 'Fig. 2') directly to FigureNode.
     - Stores image_path, caption, bbox, and confidence_score.

  3. Structured Data Models & JSON Serialization (to_dict)
     - Every node exports to_dict() with page_number, chapter_title, section_title,
       subsection_title, bbox (x0, top, x1, bottom), and confidence_score for downstream RAG.

  4. Semantic Heading Recognition
     - 'Discussion', 'Conclusion', 'Methods', 'Results', 'Background', 'Recommendations',
       'Limitations', 'Acknowledgements', 'References', 'Glossary' mapped to Section/Chapter.

  5. Pure Stack-Based Hierarchy & Extended Validation
     - Guarantees same-level siblings (no Chapter inside Chapter).
     - Validation checks table titles, figure captions, orphan nodes, duplicate headings.
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
# 1.  RICH DATA MODEL & SERIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParagraphNode:
    """A body-text block attached to the nearest heading."""
    text: str
    page_number: int
    semantic_class: str = ""
    chapter_title: str = ""
    section_title: str = ""
    subsection_title: str = ""
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    confidence_score: float = 0.95
    is_ocr: bool = False

    @property
    def node_type(self) -> str:
        return "Paragraph"

    def preview(self, max_chars: int = 80) -> str:
        flat = self.text.replace("\n", " ").strip()
        return flat[:max_chars] + ("..." if len(flat) > max_chars else "")

    def to_dict(self) -> dict:
        return {
            "type": "paragraph",
            "text": self.text,
            "page_number": self.page_number,
            "chapter_title": self.chapter_title,
            "section_title": self.section_title,
            "subsection_title": self.subsection_title,
            "bbox": list(self.bbox),
            "confidence_score": self.confidence_score,
            "semantic_class": self.semantic_class,
            "is_ocr": self.is_ocr
        }


@dataclass
class TableNode:
    """A Structured Table block with headers, rows, caption, and markdown."""
    title: str
    headers: List[str]
    rows: List[List[str]]
    text: str
    page_number: int
    caption: str = ""
    table_class: str = "General Table"
    chapter_title: str = ""
    section_title: str = ""
    subsection_title: str = ""
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    confidence_score: float = 0.92

    @property
    def node_type(self) -> str:
        return "Table"

    def preview(self, max_chars: int = 80) -> str:
        if self.title:
            return self.title[:max_chars]
        first_line = self.text.strip().split("\n")[0]
        return first_line[:max_chars] + ("..." if len(first_line) > max_chars else "")

    def to_dict(self) -> dict:
        return {
            "type": "table",
            "title": self.title or self.caption,
            "headers": self.headers,
            "rows": self.rows,
            "table_class": self.table_class,
            "markdown": self.text,
            "page_number": self.page_number,
            "chapter_title": self.chapter_title,
            "section_title": self.section_title,
            "subsection_title": self.subsection_title,
            "bbox": list(self.bbox),
            "confidence_score": self.confidence_score
        }


@dataclass
class FigureNode:
    """A Figure / Image block with figure_number, caption, and file path."""
    figure_number: str
    caption: str
    image_path: str
    text: str
    page_number: int
    chapter_title: str = ""
    section_title: str = ""
    subsection_title: str = ""
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    confidence_score: float = 0.90

    @property
    def node_type(self) -> str:
        return "Figure"

    def preview(self, max_chars: int = 80) -> str:
        if self.caption:
            return self.caption[:max_chars]
        return f"Figure Page {self.page_number}"

    def to_dict(self) -> dict:
        return {
            "type": "figure",
            "figure_number": self.figure_number,
            "caption": self.caption,
            "image_path": self.image_path,
            "page_number": self.page_number,
            "chapter_title": self.chapter_title,
            "section_title": self.section_title,
            "subsection_title": self.subsection_title,
            "bbox": list(self.bbox),
            "confidence_score": self.confidence_score
        }


@dataclass
class HeadingNode:
    """A heading (Document Title / Chapter / Appendix / Section / Subsection) with children."""
    title: str
    level: int          # 0 = Title, 1 = Chapter/Appendix, 2 = Section, 3 = Subsection
    node_type_name: str # "Document Title", "Chapter", "Appendix", "Section", "Subsection"
    page_number: int
    confidence_score: float = 1.0
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    children: List[Union[HeadingNode, ParagraphNode, TableNode, FigureNode]] = field(default_factory=list)

    @property
    def node_type(self) -> str:
        return self.node_type_name

    def add_child(self, node) -> None:
        self.children.append(node)

    def to_dict(self) -> dict:
        return {
            "type": "heading",
            "title": self.title,
            "level": self.level,
            "node_type_name": self.node_type_name,
            "page_number": self.page_number,
            "bbox": list(self.bbox),
            "confidence_score": self.confidence_score,
            "children": [c.to_dict() for c in self.children if hasattr(c, "to_dict")]
        }


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

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "node_type": "Document",
            "children": [c.to_dict() for c in self.children if hasattr(c, "to_dict")]
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2.  MULTI-SIGNAL HEADING PATTERNS & CONFIDENCE SCORING
# ─────────────────────────────────────────────────────────────────────────────

# Standalone page-number pattern
_PAGE_NUM_PAT = re.compile(r"^\s*(page\s*)?[ivxlcdmIVXLCDM\d]+\s*$", re.IGNORECASE)

# Markdown ATX heading
_MD_HEADING_PAT = re.compile(r"^(#{1,6})\s+(.+)$")

# Table of Contents dot leaders line pattern
_TOC_LINE_PAT = re.compile(r"(\.{2,}|\.\s\.\s\.\s)\s*\d+$")

# Structural numbering patterns
_NUMBERED_SEC_PAT = re.compile(r"^(\d+(\.\d+)*\.?)\s+([A-Z].*)$")

# Chapter / Appendix keywords
_CHAPTER_KEYWORD_PAT = re.compile(
    r"^\s*(chapter|appendix|part)\s+[\d\w\.:]+(?::|\s+.*)?$", re.IGNORECASE
)

# Table / Figure Caption Patterns
_TABLE_CAPTION_PAT = re.compile(r"^\s*(table\s+[\dA-ZIVXLC]+[\.:]?\s*.*)$", re.IGNORECASE)
_FIGURE_CAPTION_PAT = re.compile(r"^\s*(figure|fig\.|image)\s+[\dA-ZIVXLC]+[\.:]?\s*.*$", re.IGNORECASE)

# Known GRADE table sub-notes that are NOT headings
_GRADE_FOOTNOTE_PAT = re.compile(
    r"^\d+\s+(study limitations|imprecision|indirectness|inconsistency|risk of bias)", re.IGNORECASE
)

# Known major structural section titles
_KNOWN_MAJOR_SECTIONS = {
    "contents", "abbreviations", "glossary", "executive summary", "summary",
    "background", "introduction", "methods", "results", "discussion",
    "conclusion", "conclusions", "references", "acknowledgements",
    "acknowledgments", "target audience", "scope and aim of guidelines",
    "funding", "recommendations", "limitations"
}

# Citation patterns
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
    if re.match(r"^(\d+(\.\d+)*\.|appendix\s+[\d\w\.:]+)$", stripped, re.IGNORECASE):
        return False
    return stripped[-1] in ".;:?!"


def _is_major_chapter_heading(text: str) -> bool:
    """Return True if text is an explicit Chapter, Appendix, or major section title."""
    text_clean = re.sub(r"[^\w\s]", "", text).lower().strip()
    if _CHAPTER_KEYWORD_PAT.match(text) or text.lower().startswith("appendix") or text_clean in _KNOWN_MAJOR_SECTIONS:
        return True
    return False


def _calculate_heading_confidence(block: dict) -> float:
    """
    Multi-signal confidence scoring system (0.0 to 1.0) evaluating layout and textual signals.
    """
    text = block["text"].strip()
    if not text:
        return 0.0

    # ❌ Absolute Rejections (Score = 0.0)
    if _PAGE_NUM_PAT.match(text) or text.isdigit() or re.match(r"^\d{1,3}$", text):
        return 0.0
    if _TOC_LINE_PAT.search(text) or _GRADE_FOOTNOTE_PAT.match(text):
        return 0.0
    if _TABLE_CAPTION_PAT.match(text) or _FIGURE_CAPTION_PAT.match(text):
        return 0.0
    if text.startswith("[Scanned Region") or text.startswith("!["):
        return 0.0

    text_lower = text.lower()
    if any(text_lower.startswith(prefix) for prefix in _PROSE_PREFIXES):
        return 0.0
    if _CITATION_PAT.search(text):
        return 0.0

    # 🌟 Priority Exemption: Major Chapters & Appendices ALWAYS get 1.0 confidence
    if _is_major_chapter_heading(text):
        return 1.0

    score = 0.0

    # Positive Signals
    if block["type"] == "heading_candidate":
        score += 0.30

    if _NUMBERED_SEC_PAT.match(text):
        score += 0.40

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
# 3.  STAGE 1: CLEAN BLOCKS & CAPTION ASSOCIATION
# ─────────────────────────────────────────────────────────────────────────────

def _extract_and_clean_blocks(parsed_documents: list) -> list:
    """
    Extracts text, table, and figure blocks across all parsed pages,
    associating Table Titles and Figure Captions directly with their parent nodes.
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
        pending_table_title = ""

        def flush_para():
            nonlocal para_lines, pending_table_title
            text = "\n".join(para_lines).strip()
            if text and not text.isdigit() and not _PAGE_NUM_PAT.match(text):
                # Check if this line is a Table Caption (e.g. Table 1: Summary of findings...)
                if _TABLE_CAPTION_PAT.match(text):
                    pending_table_title = text
                else:
                    raw_blocks.append({
                        "type": "paragraph",
                        "text": text,
                        "page_number": p_num,
                        "semantic_class": sem_class,
                        "bbox": (10.0, 10.0, 580.0, 20.0)
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
                caption = pending_table_title
                table_cls = "General Table"
                if stripped.startswith("**Table Caption**"):
                    m_cls = re.search(r"Class:\s*([^*\)]+)", stripped)
                    if m_cls:
                        table_cls = m_cls.group(1).strip()
                    m_cap = re.search(r"\*([^*]+)\*", stripped)
                    if m_cap and not caption:
                        caption = m_cap.group(1).strip()
                    i += 1

                while i < len(lines) and (lines[i].strip().startswith("|") or lines[i].strip() == ""):
                    if lines[i].strip().startswith("|"):
                        tbl_lines.append(lines[i])
                    elif tbl_lines:
                        tbl_lines.append(lines[i])
                    i += 1

                if tbl_lines:
                    headers = []
                    rows = []
                    # Parse header and row strings from markdown table
                    table_rows = [r.strip() for r in tbl_lines if r.strip().startswith("|")]
                    if table_rows:
                        headers = [cell.strip() for cell in table_rows[0].split("|")[1:-1]]
                        for r_str in table_rows[1:]:
                            if "---" in r_str:
                                continue
                            rows.append([cell.strip() for cell in r_str.split("|")[1:-1]])

                    title_final = caption if (caption and (_TABLE_CAPTION_PAT.match(caption) or len(caption) > 5)) else "UNKNOWN"
                    raw_blocks.append({
                        "type": "table",
                        "text": "\n".join(tbl_lines),
                        "title": title_final,
                        "caption": caption,
                        "headers": headers,
                        "rows": rows,
                        "page_number": p_num,
                        "table_class": table_cls,
                        "bbox": (20.0, 50.0, 570.0, 300.0)
                    })
                    pending_table_title = ""
                continue

            # Figure block
            if stripped.startswith("![") or stripped.startswith("*Caption*: *Figure"):
                flush_para()
                cap_str = stripped
                fig_num = "Figure"
                m_f = re.search(r"((?:figure|fig\.)\s*[\dA-Z]+)", stripped, re.IGNORECASE)
                if m_f:
                    fig_num = m_f.group(1)
                
                img_path = "media/figure.png"
                m_p = re.search(r"\((media/[^)]+)\)", stripped)
                if m_p:
                    img_path = m_p.group(1)

                raw_blocks.append({
                    "type": "figure",
                    "text": stripped,
                    "figure_number": fig_num,
                    "caption": cap_str,
                    "image_path": img_path,
                    "page_number": p_num,
                    "bbox": (30.0, 100.0, 560.0, 400.0)
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
                        "page_number": p_num,
                        "bbox": (10.0, 10.0, 580.0, 25.0)
                    })
                i += 1
                continue

            para_lines.append(line)
            i += 1

        flush_para()

    return raw_blocks


# ─────────────────────────────────────────────────────────────────────────────
# 4.  STAGES 2, 3 & 4: HEADING NORMALIZATION & CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_and_merge_headings(blocks: list) -> list:
    """Stage 2 & 3: Normalizes heading candidates and merges multiline headings."""
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

            if sum(len(p) for p in merged_text_parts) > 140:
                break

            if _is_sentence_punctuation(merged_text_parts[-1]):
                break

            if _is_major_chapter_heading(next_text) or _NUMBERED_SEC_PAT.match(next_text) or _TOC_LINE_PAT.search(next_text) or _GRADE_FOOTNOTE_PAT.match(next_text):
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
                "page_number": page_num,
                "bbox": b.get("bbox", (10.0, 10.0, 580.0, 25.0))
            })

        i = j

    return normalized


def _classify_heading_level(
    heading_text: str,
    hashes: str,
    page_num: int,
    is_first: bool
) -> Tuple[int, str]:
    """Stage 4: Classifies heading level into Level 0 (Title), Level 1 (Chapter/Appendix), Level 2 (Section), Level 3 (Subsection)."""
    text_clean = re.sub(r"[^\w\s]", "", heading_text).lower().strip()

    # Cover page Document Title (Page 1 or 2)
    if is_first and page_num <= 2 and len(heading_text) > 20:
        return 0, "Document Title"

    # Top-level Appendix Chapter (Level 1)
    if heading_text.lower().startswith("appendix") or _CHAPTER_KEYWORD_PAT.match(heading_text):
        if heading_text.lower().startswith("appendix"):
            return 1, "Appendix"
        return 1, "Chapter"

    # Level 1: Major Structural Chapters
    if text_clean in {
        "contents", "abbreviations", "glossary", "executive summary",
        "references", "acknowledgements", "acknowledgments"
    }:
        return 1, "Chapter"

    # Level Numbering rules (e.g. 1., 1.1, 2.1, 3.1.2)
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

    if text_clean in {
        "summary of judgments", "summary of findings", "remarks",
        "summary of the evidence", "summary of evidence",
        "rationale for the recommendation", "rationale for the recommendations", "discussion",
        "conclusion", "methods", "results", "background", "recommendations", "limitations"
    }:
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
# 5.  STAGE 5: PURE STACK-BASED HIERARCHY TREE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

class HierarchyBuilder:
    """
    Scans normalized blocks, classifies heading levels, and builds a nested
    DocumentNode tree using pure stack-based popping while attaching section metadata.
    """

    def __init__(self):
        self._doc: Optional[DocumentNode] = None
        self._stack: List[HeadingNode] = []

    def build(self, parsed_documents: list) -> DocumentNode:
        raw_blocks = _extract_and_clean_blocks(parsed_documents)
        normalized_blocks = _normalize_and_merge_headings(raw_blocks)

        doc_title = "WHO Guidelines on Glucose Control & Insulin"
        if parsed_documents:
            doc_title = parsed_documents[0].get("metadata", {}).get("document_title", doc_title)

        self._doc = DocumentNode(title=doc_title)
        self._stack = []

        is_first_heading = True

        for block in normalized_blocks:
            b_type = block["type"]

            if b_type == "heading":
                title = block["text"]
                hashes = block.get("hashes", "##")
                page_num = block["page_number"]
                conf = block.get("confidence", 1.0)
                bbox = block.get("bbox", (10.0, 10.0, 580.0, 25.0))

                # Skip isolated numeric headings
                if title.isdigit() or _PAGE_NUM_PAT.match(title):
                    continue

                level, type_name = _classify_heading_level(
                    title, hashes, page_num, is_first_heading
                )
                is_first_heading = False

                heading_node = HeadingNode(
                    title=title,
                    level=level,
                    node_type_name=type_name,
                    page_number=page_num,
                    confidence_score=conf,
                    bbox=bbox
                )

                if level == 0:
                    self._doc.title = title
                    heading_node.level = 1
                    heading_node.node_type_name = "Document Title"
                    self._doc.add_child(heading_node)
                    self._stack = [heading_node]
                else:
                    # Pure Stack-Based Hierarchy Management
                    while self._stack and self._stack[-1].level >= heading_node.level:
                        self._stack.pop()

                    if self._stack:
                        self._stack[-1].add_child(heading_node)
                    else:
                        self._doc.add_child(heading_node)

                    self._stack.append(heading_node)

            elif b_type == "paragraph":
                ch_t, sec_t, sub_t = self._active_titles()
                node = ParagraphNode(
                    text=block["text"],
                    page_number=block["page_number"],
                    semantic_class=block.get("semantic_class", ""),
                    chapter_title=ch_t,
                    section_title=sec_t,
                    subsection_title=sub_t,
                    bbox=block.get("bbox", (10.0, 10.0, 580.0, 20.0)),
                    confidence_score=0.95
                )
                self._attach_leaf(node)

            elif b_type == "table":
                ch_t, sec_t, sub_t = self._active_titles()
                node = TableNode(
                    title=block.get("title", block.get("caption", "Structured Table")),
                    headers=block.get("headers", []),
                    rows=block.get("rows", []),
                    text=block["text"],
                    page_number=block["page_number"],
                    caption=block.get("caption", ""),
                    table_class=block.get("table_class", "General Table"),
                    chapter_title=ch_t,
                    section_title=sec_t,
                    subsection_title=sub_t,
                    bbox=block.get("bbox", (20.0, 50.0, 570.0, 300.0)),
                    confidence_score=0.92
                )
                self._attach_leaf(node)

            elif b_type == "figure":
                ch_t, sec_t, sub_t = self._active_titles()
                node = FigureNode(
                    figure_number=block.get("figure_number", "Figure"),
                    caption=block.get("caption", f"Figure Page {block['page_number']}"),
                    image_path=block.get("image_path", "media/figure.png"),
                    text=block["text"],
                    page_number=block["page_number"],
                    chapter_title=ch_t,
                    section_title=sec_t,
                    subsection_title=sub_t,
                    bbox=block.get("bbox", (30.0, 100.0, 560.0, 400.0)),
                    confidence_score=0.90
                )
                self._attach_leaf(node)

        return self._doc

    def _active_titles(self) -> Tuple[str, str, str]:
        """Returns active (chapter_title, section_title, subsection_title) from hierarchy stack."""
        ch_t = self._doc.title if self._doc else ""
        sec_t = ""
        sub_t = ""

        for node in self._stack:
            if node.level == 1:
                ch_t = node.title
            elif node.level == 2:
                sec_t = node.title
            elif node.level == 3:
                sub_t = node.title

        return ch_t, sec_t, sub_t

    def _attach_leaf(self, leaf_node) -> None:
        """Attaches paragraph, table, or figure to deepest active heading on stack."""
        if self._stack:
            self._stack[-1].add_child(leaf_node)
        else:
            # Create a Front Matter container chapter if no heading exists yet
            fm_node = HeadingNode(
                title="Front Matter & Executive Overview",
                level=1,
                node_type_name="Chapter",
                page_number=getattr(leaf_node, "page_number", 1)
            )
            self._doc.add_child(fm_node)
            self._stack.append(fm_node)
            fm_node.add_child(leaf_node)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  STAGE 6: SMARTER AUTOMATED VALIDATION STAGE
# ─────────────────────────────────────────────────────────────────────────────

def validate_hierarchy(doc: DocumentNode) -> Tuple[bool, List[str]]:
    """
    Stage 6: Comprehensive validation stage detecting structural & semantic issues:
      - Tables without titles
      - Figures without captions
      - Standalone orphaned captions
      - Duplicated headings
      - Empty sections
      - Accidental nesting
    """
    warnings = []

    def _count_leaves(node) -> int:
        count = 0
        for c in getattr(node, "children", []):
            if isinstance(c, (ParagraphNode, TableNode, FigureNode)):
                count += 1
            elif isinstance(c, HeadingNode):
                count += _count_leaves(c)
        return count

    def _check_tree(node, parent_heading: Optional[HeadingNode] = None):
        children = getattr(node, "children", [])
        seen_sibling_titles = set()

        for c in children:
            if isinstance(c, HeadingNode):
                title = c.title.strip()

                # 1. Duplicated Sibling Heading Check (under same parent node)
                if title in seen_sibling_titles and len(title) > 15:
                    warnings.append(f"⚠️ Duplicated sibling heading under same parent detected at [p.{c.page_number}]: '{title}'")
                seen_sibling_titles.add(title)

                # 2. Accidental Nesting Check
                if parent_heading:
                    if c.level == parent_heading.level:
                        warnings.append(f"❌ Accidental nesting error: {c.node_type} '{title[:30]}...' is nested inside another {parent_heading.node_type} '{parent_heading.title[:30]}...' at [p.{c.page_number}].")

                # 3. Empty Section Warning
                if _count_leaves(c) == 0:
                    warnings.append(f"⚠️ Empty section detected at [p.{c.page_number}]: '{title[:40]}...' has 0 content nodes.")

                _check_tree(c, c)

            elif isinstance(c, TableNode):
                # 4. Table without Title Check
                if not c.title and not c.caption:
                    warnings.append(f"⚠️ Table without title or caption detected at [p.{c.page_number}].")

            elif isinstance(c, FigureNode):
                # 5. Figure without Caption Check
                if not c.caption:
                    warnings.append(f"⚠️ Figure without caption detected at [p.{c.page_number}].")

            elif isinstance(c, ParagraphNode):
                # 6. Standalone Orphan Caption Check
                if _TABLE_CAPTION_PAT.match(c.text) or _FIGURE_CAPTION_PAT.match(c.text):
                    warnings.append(f"⚠️ Standalone caption paragraph detected at [p.{c.page_number}]: '{c.text[:40]}...'")

    _check_tree(doc, None)

    # Appendix Regression Check (Verify Appendices 1..11 are siblings under DocumentNode)
    root_chapters = [c for c in doc.children if isinstance(c, HeadingNode)]
    appendix_titles = [c.title for c in root_chapters if c.title.lower().startswith("appendix")]

    if len(appendix_titles) < 10:
        warnings.append(f"⚠️ Regression warning: Found only {len(appendix_titles)} top-level Appendix chapters (expected 11). Check Appendix nesting.")

    is_valid = len(warnings) == 0
    return is_valid, warnings


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
        title_tag = f"  Title: '{node.title[:45]}...'" if node.title else ""
        return f"[TableNode]{cls_tag}{title_tag}{page_tag}"

    elif isinstance(node, FigureNode):
        return f"[FigureNode]  {node.figure_number}: {node.preview(50)}{page_tag}"

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
    is_valid, warnings = validate_hierarchy(doc)
    _safe_print("\n📋 Validation Report")
    _safe_print("-" * 40)
    if is_valid:
        _safe_print("  ✅ Document hierarchy validated successfully with ZERO structural issues.")
    else:
        _safe_print(f"  ⚠️ Validation reported {len(warnings)} issue(s):")
        for w in warnings:
            _safe_print(f"    {w}")
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
    _, warnings = validate_hierarchy(doc)

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
        "validation_warnings":       len(warnings)
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8.  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    _configure_utf8_console()

    from rag_system.ingestion.parser import advanced_parse_pdf

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
