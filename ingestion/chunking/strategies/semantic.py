"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Semantic Prose Strategy
=============================================================================
  Handles normal prose paragraphs, building structure-aware semantic chunks
  with configurable target/max size caps and sentence-boundary overlap.
=============================================================================
"""

from __future__ import annotations

import re
from typing import List, Dict, Any
from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.strategies.base import ChunkingStrategy
from ingestion.chunking.utils.token_utils import TokenCounter


class SemanticChunkingStrategy(ChunkingStrategy):
    """Semantic chunking strategy for normal prose paragraphs."""

    def can_handle(self, block: StructuralBlock) -> bool:
        return block.content_type in (ContentType.PARAGRAPH, ContentType.HEADING)

    def chunk(
        self,
        block: StructuralBlock,
        context: Dict[str, Any],
        config: ChunkingConfig,
        token_counter: TokenCounter
    ) -> List[StructureAwareChunk]:
        """
        Chunks prose block respecting sentence boundaries, target tokens, and overlap.
        """
        chunks = []
        doc_prefix = context.get("doc_prefix", "chk")
        doc_title = context.get("doc_title", "WHO Guidelines")

        text = block.text.strip()
        t_count = token_counter.count(text)

        if t_count <= config.max_chunk_tokens:
            chk_id = f"chk_{doc_prefix}_text_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            chunk = StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                content_type=ContentType.PARAGRAPH,
                title=block.title or block.section or block.chapter,
                content=text,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=t_count,
                table_references=[],
                figure_references=[],
                metadata={
                    "page_start": block.page_number,
                    "page_end": block.page_number,
                    "node_type": "Paragraph"
                }
            )
            return [chunk]

        # Splitting large prose on sentence boundaries
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        if not sentences:
            sentences = [text]

        current_sentences = []
        current_tokens = 0

        for s in sentences:
            s_tokens = token_counter.count(s)

            if current_tokens + s_tokens > config.target_chunk_tokens and current_sentences:
                chunk_text = " ".join(current_sentences)
                chk_id = f"chk_{doc_prefix}_text_{context.get('chunk_counter', 1):04d}"
                context["chunk_counter"] = context.get("chunk_counter", 1) + 1

                chunks.append(StructureAwareChunk(
                    chunk_id=chk_id,
                    document_title=doc_title,
                    chapter=block.chapter,
                    section=block.section,
                    subsection=block.subsection,
                    content_type=ContentType.PARAGRAPH,
                    title=block.title or block.section or block.chapter,
                    content=chunk_text,
                    embedding_text="",
                    page_start=block.page_number,
                    page_end=block.page_number,
                    token_count=token_counter.count(chunk_text),
                    metadata={"page_start": block.page_number, "page_end": block.page_number}
                ))

                # Sentence-boundary overlap window
                overlap_sentences = []
                overlap_tokens = 0
                for prev_s in reversed(current_sentences):
                    prev_tokens = token_counter.count(prev_s)
                    if overlap_tokens + prev_tokens <= config.overlap_tokens:
                        overlap_sentences.insert(0, prev_s)
                        overlap_tokens += prev_tokens
                    else:
                        break

                current_sentences = overlap_sentences + [s]
                current_tokens = sum(token_counter.count(item) for item in current_sentences)
            else:
                current_sentences.append(s)
                current_tokens += s_tokens

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chk_id = f"chk_{doc_prefix}_text_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            chunks.append(StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                content_type=ContentType.PARAGRAPH,
                title=block.title or block.section or block.chapter,
                content=chunk_text,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=token_counter.count(chunk_text),
                metadata={"page_start": block.page_number, "page_end": block.page_number}
            ))

        return chunks
