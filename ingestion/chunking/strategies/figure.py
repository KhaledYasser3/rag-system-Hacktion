"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Figure Strategy
=============================================================================
  Handles Figure blocks, preserving caption, image path, and figure metadata
  as atomic units.
=============================================================================
"""

from __future__ import annotations

from typing import List, Dict, Any
from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.strategies.base import ChunkingStrategy
from ingestion.chunking.utils.token_utils import TokenCounter


class FigureChunkingStrategy(ChunkingStrategy):
    """Chunking strategy specifically designed for Figures."""

    def can_handle(self, block: StructuralBlock) -> bool:
        return block.content_type == ContentType.FIGURE

    def chunk(
        self,
        block: StructuralBlock,
        context: Dict[str, Any],
        config: ChunkingConfig,
        token_counter: TokenCounter
    ) -> List[StructureAwareChunk]:
        doc_prefix = context.get("doc_prefix", "chk")
        doc_title = context.get("doc_title", "WHO Guidelines")

        chk_id = f"chk_{doc_prefix}_fig_{context.get('chunk_counter', 1):04d}"
        context["chunk_counter"] = context.get("chunk_counter", 1) + 1

        fig_meta = block.metadata.get("figure_meta", {})
        fig_ref = [fig_meta] if fig_meta else []

        chunk = StructureAwareChunk(
            chunk_id=chk_id,
            document_title=doc_title,
            chapter=block.chapter,
            section=block.section,
            subsection=block.subsection,
            content_type=ContentType.FIGURE,
            title=block.title or fig_meta.get("caption", f"Figure Page {block.page_number}"),
            content=block.text.strip(),
            embedding_text="",
            page_start=block.page_number,
            page_end=block.page_number,
            token_count=token_counter.count(block.text.strip()),
            table_references=[],
            figure_references=fig_ref,
            metadata=block.metadata
        )
        return [chunk]
