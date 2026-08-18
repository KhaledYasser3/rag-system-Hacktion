"""
=============================================================================
  MODULAR PDF PARSER — Typed Data Models
=============================================================================
  Intermediate representation models for extracted pages and content blocks.
  Guarantees explicit separation between TITLE/HEADING and CONTENT/DEFINITION.
=============================================================================
"""

from __future__ import annotations

import time
import tracemalloc
from enum import Enum
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


class BlockType(str, Enum):
    """Explicit content block classifications."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    GLOSSARY_ENTRY = "glossary_entry"
    TABLE = "table"
    LIST = "list"
    FIGURE = "figure"
    CAPTION = "caption"
    UNKNOWN = "unknown"


@dataclass
class ContentBlock:
    """A structural content block extracted from a PDF page."""
    block_id: str
    page_number: int
    block_type: BlockType
    content: str                          # Actual content / definition / body text / markdown
    title: str = ""                       # Heading text, glossary term name, table title, figure caption
    headers: List[str] = field(default_factory=list)      # Table headers if table
    rows: List[List[str]] = field(default_factory=list)   # Table rows if table
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    reading_order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "page_number": self.page_number,
            "block_type": self.block_type.value,
            "title": self.title,
            "content": self.content,
            "headers": self.headers,
            "rows": self.rows,
            "bbox": list(self.bbox),
            "reading_order": self.reading_order,
            "metadata": self.metadata,
        }


@dataclass
class ParsedPage:
    """Intermediate parsed representation of a single PDF page."""
    page_number: int
    width: float
    height: float
    blocks: List[ContentBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "metadata": self.metadata,
            "blocks": [b.to_dict() for b in self.blocks],
        }


@dataclass
class ParsedDocument:
    """Complete parsed document object representing the entire PDF."""
    document_id: str
    title: str
    source_filename: str
    pages: List[ParsedPage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source_filename": self.source_filename,
            "total_pages": len(self.pages),
            "metadata": self.metadata,
            "pages": [p.to_dict() for p in self.pages],
        }

    def to_legacy_pages(self) -> List[dict]:
        """
        Converts ParsedDocument into legacy dict representation expected by
        downstream HierarchyBuilder.
        """
        legacy_list = []
        for p in sorted(self.pages, key=lambda x: x.page_number):
            # Assemble page markdown text from content blocks
            page_text_parts = []
            has_tables = False
            for b in sorted(p.blocks, key=lambda x: (x.reading_order, x.bbox[1])):
                if b.block_type == BlockType.GLOSSARY_ENTRY:
                    term = b.title.strip()
                    defn = b.content.strip()
                    page_text_parts.append(f"{term}\n{defn}")
                elif b.block_type == BlockType.TABLE:
                    has_tables = True
                    if b.title and not b.title.startswith("Table Page"):
                        page_text_parts.append(f"**{b.title}**")
                    page_text_parts.append(b.content)
                elif b.block_type == BlockType.FIGURE:
                    page_text_parts.append(b.content)
                elif b.block_type == BlockType.HEADING:
                    page_text_parts.append(f"## {b.title}")
                else:
                    page_text_parts.append(b.content)

            full_page_text = "\n\n".join(page_text_parts).strip()
            ch = p.metadata.get("chapter", "General Context")
            sec = p.metadata.get("section", "General Section")
            sub = p.metadata.get("subsection", "General Subsection")

            legacy_list.append({
                "page_number": p.page_number,
                "content": full_page_text,
                "metadata": {
                    "source": self.source_filename,
                    "page_number": p.page_number,
                    "document_title": self.title,
                    "chapter": ch,
                    "section": sec,
                    "subsection": sub,
                    "is_ocr": p.metadata.get("is_ocr", False),
                    "language": p.metadata.get("language", "English"),
                    "word_count": len(full_page_text.split()),
                    "char_count": len(full_page_text),
                    "has_tables": has_tables or ("|\n|" in full_page_text),
                    "layout_type": p.metadata.get("layout_type", "single_column"),
                    "semantic_class": p.metadata.get("semantic_class", "General Context")
                }
            })
        return legacy_list


class AdvancedQualityTracker:
    """Tracks metrics, execution profile, and error diagnostics for Parser Quality Reporting."""
    def __init__(self):
        self.start_time = 0
        self.end_time = 0
        self.peak_memory_mb = 0.0
        self.total_pages = 0
        self.parsed_pages = 0
        self.ocr_fallbacks = 0
        self.tables_extracted = 0
        self.tables_by_class = Counter()
        self.figures_extracted = 0
        self.columns_processed = 0
        self.glossary_entries_extracted = 0
        self.errors = []

    def start(self):
        self.start_time = time.perf_counter()
        tracemalloc.start()

    def stop(self):
        self.end_time = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        self.peak_memory_mb = peak / (1024 * 1024)
        tracemalloc.stop()

    def elapsed_time(self):
        return self.end_time - self.start_time

    def generate_report(self, output_path="parsing_quality_report.md"):
        accuracy = (self.parsed_pages / self.total_pages * 100) if self.total_pages > 0 else 0
        report = f"""# 📄 Modular PDF Parsing Quality & Diagnostic Report

## 📊 Performance Metrics
- **Total Pages Analyzed**: {self.total_pages}
- **Parsing Success Rate**: {self.parsed_pages}/{self.total_pages} ({accuracy:.1f}%)
- **Region-based OCR Operations**: {self.ocr_fallbacks}
- **Glossary Entries Extracted**: {self.glossary_entries_extracted}
- **Figures Extracted**: {self.figures_extracted}
- **Tables Extracted**: {self.tables_extracted}

## ⚡ Runtime Profile
- **Total Execution Time**: {self.elapsed_time():.2f} seconds
- **Throughput Rate**: {(self.elapsed_time() / self.total_pages if self.total_pages else 0):.2f} seconds/page
- **Peak RAM Allocation**: {self.peak_memory_mb:.2f} MB
"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
        except Exception:
            pass

# Compatibility alias
QualityTracker = AdvancedQualityTracker
