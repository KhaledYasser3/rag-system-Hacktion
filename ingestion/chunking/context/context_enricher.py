"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Context Enricher
=============================================================================
  Constructs contextualized embedding_text representations separate from raw
  source content, ensuring every chunk is self-contained and understandable
  independently during vector retrieval.
=============================================================================
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from ingestion.chunking.models import StructureAwareChunk, ContentType
from ingestion.chunking.config import ChunkingConfig


class ContextEnricher:
    """Enriches chunk objects with structured hierarchy and contextual embedding_text."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()

    def enrich(self, chunk: StructureAwareChunk) -> StructureAwareChunk:
        """Generates contextualized embedding_text for the chunk."""
        parts = []

        if chunk.document_title:
            parts.append(f"Document: {chunk.document_title}")
        if chunk.chapter:
            parts.append(f"Chapter: {chunk.chapter}")
        if chunk.section:
            parts.append(f"Section: {chunk.section}")
        if chunk.subsection:
            parts.append(f"Subsection: {chunk.subsection}")

        if chunk.content_type == ContentType.GLOSSARY_ENTRY and chunk.title:
            parts.append(f"Term: {chunk.title}")
        elif chunk.title:
            parts.append(f"Title: {chunk.title}")

        header_prefix = "\n".join(parts)

        if header_prefix:
            contextualized_text = f"{header_prefix}\n\nContent:\n{chunk.content}".strip()
        else:
            contextualized_text = chunk.content.strip()

        chunk.embedding_text = contextualized_text
        return chunk
