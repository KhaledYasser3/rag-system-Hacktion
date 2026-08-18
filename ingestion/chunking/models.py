"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Data Models
=============================================================================
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union


class ContentType(str, Enum):
    """Supported content classifications for structural blocks."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    GLOSSARY_ENTRY = "glossary_entry"
    TABLE = "table"
    LIST = "list"
    FIGURE = "figure"


@dataclass
class StructuralBlock:
    """Normalized internal representation of an extracted node/block from HierarchyBuilder."""
    block_id: str
    content_type: ContentType
    text: str
    page_number: int
    chapter: str = ""
    section: str = ""
    subsection: str = ""
    title: str = ""                    # Term for glossary, Caption for table/figure, Title for heading
    headers: List[str] = field(default_factory=list)      # Table headers if table
    rows: List[List[str]] = field(default_factory=list)   # Table rows if table
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_node: Any = None               # Reference to original ParagraphNode/TableNode/FigureNode

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "content_type": self.content_type.value,
            "text": self.text,
            "page_number": self.page_number,
            "chapter": self.chapter,
            "section": self.section,
            "subsection": self.subsection,
            "title": self.title,
            "headers": self.headers,
            "rows": len(self.rows),
            "metadata": self.metadata,
        }


@dataclass
class StructureAwareChunk:
    """
    Final chunk object produced by the Structure-Aware Chunking System.
    Separates actual source 'content' from contextualized 'embedding_text'.
    """
    chunk_id: str
    document_title: str
    chapter: str
    section: str
    subsection: str
    content_type: ContentType
    title: str                          # Heading title, Glossary term, Table title, or Figure caption
    content: str                        # Original clean content
    embedding_text: str                 # Contextualized text representation prepared for vector embedding
    page_start: int
    page_end: int
    token_count: int
    table_references: List[str] = field(default_factory=list)
    figure_references: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """JSON-serializable representation matching system schema."""
        return {
            "chunk_id": self.chunk_id,
            "document_title": self.document_title,
            "chapter": self.chapter,
            "section": self.section,
            "subsection": self.subsection,
            "content_type": self.content_type.value,
            "title": self.title,
            "content": self.content,
            "embedding_text": self.embedding_text,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "token_count": self.token_count,
            "table_references": self.table_references,
            "figure_references": self.figure_references,
            "metadata": self.metadata,
        }
