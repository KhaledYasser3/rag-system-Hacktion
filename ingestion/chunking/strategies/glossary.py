"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Glossary Strategy
=============================================================================
  Handles Glossary and Definition blocks, preserving individual term-definition
  pairs as atomic, independent semantic retrieval units.
=============================================================================
"""

from __future__ import annotations

import re
from typing import List, Dict, Any
from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.strategies.base import ChunkingStrategy
from ingestion.chunking.utils.token_utils import TokenCounter


class GlossaryChunkingStrategy(ChunkingStrategy):
    """Chunking strategy specifically designed for Glossary entries."""

    def can_handle(self, block: StructuralBlock) -> bool:
        return block.content_type == ContentType.GLOSSARY_ENTRY

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

        # 1. Handle Glossary Table blocks (PDF table detected in Glossary section)
        if block.headers or block.rows:
            entries = self._extract_entries_from_table(block)
        else:
            entries = self._extract_entries_from_text(block.text)

        # 2. Convert each term-definition entry into an atomic, independent chunk
        for term, definition in entries:
            clean_term = term.strip()
            clean_def = definition.strip()

            if not clean_term or not clean_def:
                continue

            full_content = f"Term: {clean_term}\n\nDefinition:\n{clean_def}"
            t_count = token_counter.count(full_content)

            # Handle edge case where a single definition is exceptionally long
            if t_count > config.max_chunk_tokens and config.split_long_glossary_definitions:
                sub_chunks = self._split_long_definition(
                    clean_term, clean_def, block, context, config, token_counter, len(chunks)
                )
                chunks.extend(sub_chunks)
            else:
                c_idx = len(chunks) + 1
                chk_id = f"chk_{doc_prefix}_glossary_{context.get('chunk_counter', 1):04d}"
                context["chunk_counter"] = context.get("chunk_counter", 1) + 1

                chunk = StructureAwareChunk(
                    chunk_id=chk_id,
                    document_title=doc_title,
                    chapter=block.chapter or "Glossary",
                    section=block.section or "Definitions",
                    subsection=block.subsection,
                    content_type=ContentType.GLOSSARY_ENTRY,
                    title=clean_term,
                    content=full_content,
                    embedding_text="", # Populated by ContextEnricher
                    page_start=block.page_number,
                    page_end=block.page_number,
                    token_count=t_count,
                    table_references=[],
                    figure_references=[],
                    metadata={
                        "page_start": block.page_number,
                        "page_end": block.page_number,
                        "term": clean_term,
                        "node_type": "GlossaryEntry"
                    }
                )
                chunks.append(chunk)

        # Fallback if parsing failed to extract explicit terms
        if not chunks and block.text.strip():
            c_idx = len(chunks) + 1
            chk_id = f"chk_{doc_prefix}_glossary_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1
            term_title = block.title if block.title else "Glossary Item"

            chunks.append(StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter or "Glossary",
                section=block.section or "Definitions",
                subsection=block.subsection,
                content_type=ContentType.GLOSSARY_ENTRY,
                title=term_title,
                content=block.text.strip(),
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=token_counter.count(block.text.strip()),
                metadata={"term": term_title}
            ))

        return chunks

    def _extract_entries_from_table(self, block: StructuralBlock) -> List[tuple[str, str]]:
        """Parses term-definition pairs from markdown table representations."""
        entries = []
        # Case A: Headers contain term and definition
        if len(block.headers) >= 2:
            term = block.headers[0]
            defn = " ".join(block.headers[1:])
            entries.append((term, defn))

        # Case B: Rows contain term/definition cells
        for row in block.rows:
            clean_cells = [c.strip() for c in row if c and c.strip()]
            if len(clean_cells) == 1:
                # Single cell box: line 1 = term, rest = definition
                lines = [l.strip() for l in clean_cells[0].split("\n") if l.strip()]
                if len(lines) >= 2:
                    entries.append((lines[0], "\n".join(lines[1:])))
                elif len(lines) == 1:
                    entries.append((lines[0], lines[0]))
            elif len(clean_cells) >= 2:
                entries.append((clean_cells[0], " ".join(clean_cells[1:])))

        return entries

    def _extract_entries_from_text(self, text: str) -> List[tuple[str, str]]:
        """Parses term-definition pairs from raw prose text blocks."""
        entries = []
        blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]

        for b in blocks:
            lines = [l.strip() for l in b.split("\n") if l.strip()]
            if not lines:
                continue

            # Check if line 1 looks like a term
            if len(lines) >= 2 and len(lines[0]) < 70 and not lines[0].endswith("."):
                term = lines[0]
                defn = "\n".join(lines[1:])
                entries.append((term, defn))
            elif ":" in lines[0] and len(lines[0].split(":")[0]) < 60:
                parts = lines[0].split(":", 1)
                term = parts[0]
                defn = parts[1] + ("\n" + "\n".join(lines[1:]) if len(lines) > 1 else "")
                entries.append((term, defn))
            else:
                # Fallback term extraction
                term = lines[0][:50]
                entries.append((term, b))

        return entries

    def _split_long_definition(
        self,
        term: str,
        definition: str,
        block: StructuralBlock,
        context: Dict[str, Any],
        config: ChunkingConfig,
        token_counter: TokenCounter,
        base_idx: int
    ) -> List[StructureAwareChunk]:
        """Splits an unusually long glossary definition while preserving term in every sub-chunk."""
        chunks = []
        doc_prefix = context.get("doc_prefix", "chk")
        doc_title = context.get("doc_title", "WHO Guidelines")

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", definition) if s.strip()]
        current_sentences = []
        current_tokens = token_counter.count(f"Term: {term}\n\nDefinition:\n")

        for s in sentences:
            s_tokens = token_counter.count(s)
            if current_tokens + s_tokens > config.max_chunk_tokens and current_sentences:
                def_part = " ".join(current_sentences)
                full_content = f"Term: {term}\n\nDefinition:\n{def_part}"

                chk_id = f"chk_{doc_prefix}_glossary_{context.get('chunk_counter', 1):04d}"
                context["chunk_counter"] = context.get("chunk_counter", 1) + 1

                chunks.append(StructureAwareChunk(
                    chunk_id=chk_id,
                    document_title=doc_title,
                    chapter=block.chapter or "Glossary",
                    section=block.section or "Definitions",
                    subsection=block.subsection,
                    content_type=ContentType.GLOSSARY_ENTRY,
                    title=f"{term} (Part {len(chunks)+1})",
                    content=full_content,
                    embedding_text="",
                    page_start=block.page_number,
                    page_end=block.page_number,
                    token_count=token_counter.count(full_content),
                    metadata={"term": term}
                ))

                current_sentences = [s]
                current_tokens = token_counter.count(f"Term: {term}\n\nDefinition:\n") + s_tokens
            else:
                current_sentences.append(s)
                current_tokens += s_tokens

        if current_sentences:
            def_part = " ".join(current_sentences)
            full_content = f"Term: {term}\n\nDefinition:\n{def_part}"
            chk_id = f"chk_{doc_prefix}_glossary_{context.get('chunk_counter', 1):04d}"
            context["chunk_counter"] = context.get("chunk_counter", 1) + 1

            chunks.append(StructureAwareChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=block.chapter or "Glossary",
                section=block.section or "Definitions",
                subsection=block.subsection,
                content_type=ContentType.GLOSSARY_ENTRY,
                title=f"{term} (Part {len(chunks)+1})" if chunks else term,
                content=full_content,
                embedding_text="",
                page_start=block.page_number,
                page_end=block.page_number,
                token_count=token_counter.count(full_content),
                metadata={"term": term}
            ))

        return chunks
