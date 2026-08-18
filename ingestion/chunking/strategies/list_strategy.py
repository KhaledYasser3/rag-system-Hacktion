"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — List Strategy
=============================================================================
  Handles bulleted and numbered List blocks, preserving list item integrity
  and repeating list titles/headers across chunk splits.
=============================================================================
"""

from __future__ import annotations

import re
from typing import List, Dict, Any
from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.strategies.base import ChunkingStrategy
from ingestion.chunking.utils.token_utils import TokenCounter


class ListChunkingStrategy(ChunkingStrategy):
    """Chunking strategy specifically designed for Lists."""

    def can_handle(self, block: StructuralBlock) -> bool:
        return block.content_type == ContentType.LIST

    def chunk(
        self,
        block: StructuralBlock,
        context: Dict[str, Any],
        config: ChunkingConfig,
        token_counter: TokenCounter
    ) -> List[StructureAwareChunk]:
        chunks = []
        doc_prefix = context.get("doc_prefix", "chk")
        doc_title = context.get("doc_title", "WHO Guidelines")

        text = block.text.strip()
        t_count = token_counter.count(text)

        if t_count <= config.max_chunk_tokens:
            chk_id = f"chk_{doc_prefix}_list_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            return [StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                content_type=ContentType.LIST,
                title=block.title or block.section or "List",
                content=text,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=t_count,
                metadata={"node_type": "List"}
            )]

        # Split long lists by items
        items = [i.strip() for i in re.split(r"\n(?=[\-\*\•\d+\.]|\([a-z0-9]+\))", text) if i.strip()]
        current_items = []
        current_tokens = 0

        for item in items:
            i_tokens = token_counter.count(item)
            if current_tokens + i_tokens > config.max_chunk_tokens and current_items:
                chunk_text = "\n".join(current_items)
                chk_id = f"chk_{doc_prefix}_list_{context.get('chunk_counter', 1):04d}"
                context["chunk_counter"] = context.get("chunk_counter", 1) + 1

                chunks.append(StructureAwareChunk(
                    chunk_id=chk_id,
                    document_title=doc_title,
                    chapter=block.chapter,
                    section=block.section,
                    subsection=block.subsection,
                    content_type=ContentType.LIST,
                    title=f"{block.title or 'List'} (Part {len(chunks)+1})",
                    content=chunk_text,
                    embedding_text="",
                    page_start=block.page_number,
                    page_end=block.page_number,
                    token_count=token_counter.count(chunk_text),
                    metadata={"page_start": block.page_number, "page_end": block.page_number}
                ))

                current_items = [item]
                current_tokens = i_tokens
            else:
                current_items.append(item)
                current_tokens += i_tokens

        if current_items:
            chunk_text = "\n".join(current_items)
            chk_id = f"chk_{doc_prefix}_list_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            chunks.append(StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                content_type=ContentType.LIST,
                title=f"{block.title or 'List'} (Part {len(chunks)+1})" if chunks else (block.title or "List"),
                content=chunk_text,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=token_counter.count(chunk_text),
                metadata={"page_start": block.page_number, "page_end": block.page_number}
            ))

        return chunks
