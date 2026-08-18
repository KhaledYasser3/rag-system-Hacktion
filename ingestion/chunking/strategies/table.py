"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Table Strategy
=============================================================================
  Handles structured Table blocks, preserving table headers and titles across
  row splits so no table row is ever orphaned.
=============================================================================
"""

from __future__ import annotations

from typing import List, Dict, Any
from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.strategies.base import ChunkingStrategy
from ingestion.chunking.utils.token_utils import TokenCounter


class TableChunkingStrategy(ChunkingStrategy):
    """Chunking strategy specifically designed for Tables."""

    def can_handle(self, block: StructuralBlock) -> bool:
        return block.content_type == ContentType.TABLE

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

        table_title = block.title or getattr(block.raw_node, "caption", "") or f"Table Page {block.page_number}"
        markdown_text = block.text.strip()
        t_count = token_counter.count(markdown_text)

        # 1. If table fits in target/max tokens, keep as single atomic chunk
        if t_count <= config.max_chunk_tokens or not block.rows:
            chk_id = f"chk_{doc_prefix}_table_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            chunk = StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                content_type=ContentType.TABLE,
                title=table_title,
                content=markdown_text,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=t_count,
                table_references=[table_title],
                figure_references=[],
                metadata={
                    "page_start": block.page_number,
                    "page_end": block.page_number,
                    "table_title": table_title,
                    "headers": block.headers,
                    "row_count": len(block.rows),
                    "node_type": "Table"
                }
            )
            return [chunk]

        # 2. Large Table: Split by rows while preserving headers in every sub-chunk
        header_markdown = ""
        if block.headers:
            header_markdown = "| " + " | ".join(block.headers) + " |\n"
            header_markdown += "| " + " | ".join(["---"] * len(block.headers)) + " |\n"

        header_context = f"**{table_title}**\n\n{header_markdown}".strip()
        base_tokens = token_counter.count(header_context)

        current_rows = []
        current_tokens = base_tokens

        for r_idx, row in enumerate(block.rows, start=1):
            row_md = "| " + " | ".join(str(cell or "").replace("\n", " ").strip() for cell in row) + " |\n"
            r_tokens = token_counter.count(row_md)

            if current_tokens + r_tokens > config.max_chunk_tokens and current_rows:
                # Finalize row batch chunk
                rows_text = "".join(current_rows)
                chunk_content = f"{header_context}\n{rows_text}".strip()

                chk_id = f"chk_{doc_prefix}_table_{context.get('chunk_counter', 1):04d}"
                context["chunk_counter"] = context.get("chunk_counter", 1) + 1

                chunks.append(StructureAwareChunk(
                    chunk_id=chk_id,
                    document_title=doc_title,
                    chapter=block.chapter,
                    section=block.section,
                    subsection=block.subsection,
                    content_type=ContentType.TABLE,
                    title=f"{table_title} (Part {len(chunks)+1})",
                    content=chunk_content,
                    embedding_text="",
                    page_start=block.page_number,
                    page_end=block.page_number,
                    token_count=token_counter.count(chunk_content),
                    table_references=[table_title],
                    metadata={
                        "table_title": table_title,
                        "part": len(chunks) + 1,
                        "headers": block.headers
                    }
                ))

                current_rows = [row_md]
                current_tokens = base_tokens + r_tokens
            else:
                current_rows.append(row_md)
                current_tokens += r_tokens

        if current_rows:
            rows_text = "".join(current_rows)
            chunk_content = f"{header_context}\n{rows_text}".strip()
            chk_id = f"chk_{doc_prefix}_table_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            chunks.append(StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter,
                section=block.section,
                subsection=block.subsection,
                content_type=ContentType.TABLE,
                title=f"{table_title} (Part {len(chunks)+1})" if chunks else table_title,
                content=chunk_content,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=token_counter.count(chunk_content),
                table_references=[table_title],
                metadata={
                    "table_title": table_title,
                    "headers": block.headers
                }
            ))

        return chunks
