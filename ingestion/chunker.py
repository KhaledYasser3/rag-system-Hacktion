"""
=============================================================================
  MEDICAL RAG PIPELINE — Structure-Aware Chunking Module (Bridge & CLI)
=============================================================================
  Bridge interface exporting SemanticChunkBuilder, export_chunks, and debug
  inspection tool using the modular ChunkingPipeline architecture.
=============================================================================
"""

from __future__ import annotations

import os
import sys
import json
import statistics
from collections import Counter
from typing import List, Dict, Any, Optional

# Ensure project root directory is in Python path for clean imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.models import StructureAwareChunk, ContentType
from ingestion.chunking.pipeline import ChunkingPipeline
from shared.utils import safe_print


class SemanticChunkBuilder:
    """
    Backwards-compatible wrapper around ChunkingPipeline for pipeline orchestrators.
    """

    def __init__(
        self,
        min_chunk_tokens: int = 50,
        target_chunk_tokens: int = 400,
        max_chunk_tokens: int = 500
    ):
        self.config = ChunkingConfig(
            min_chunk_tokens=min_chunk_tokens,
            target_chunk_tokens=target_chunk_tokens,
            max_chunk_tokens=max_chunk_tokens
        )
        self.pipeline = ChunkingPipeline(config=self.config)

    def build_chunks(self, doc_tree: Any) -> List[StructureAwareChunk]:
        """Runs the structure-aware chunking pipeline."""
        return self.pipeline.run(doc_tree)


def export_chunks(
    chunks: List[StructureAwareChunk],
    json_path: str = os.path.join("data", "chunks", "chunks.json"),
    jsonl_path: str = os.path.join("data", "chunks", "chunks.jsonl")
) -> None:
    """Exports list of StructureAwareChunk objects to JSON and JSONL on disk."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)

    chunk_dicts = [c.to_dict() if hasattr(c, "to_dict") else c for c in chunks]

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)

    # Save JSONL
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c_dict in chunk_dicts:
            f.write(json.dumps(c_dict, ensure_ascii=False) + "\n")

    safe_print(f"✅ Exported {len(chunks)} chunks -> '{json_path}' and '{jsonl_path}'")


def print_chunk_statistics(doc_tree: Any, chunks: List[StructureAwareChunk]) -> None:
    """Prints comprehensive chunking statistics and breakdown by content type, chapter, and page."""
    if not chunks:
        safe_print("⚠️ No chunks available for statistics calculation.")
        return

    tokens = [c.token_count for c in chunks]
    type_counts = Counter(getattr(c, "content_type", "paragraph") for c in chunks)
    chapter_counts = Counter(getattr(c, "chapter", "General") for c in chunks)
    page_counts = Counter(getattr(c, "page_start", 1) for c in chunks)

    # Figure validation
    fig_refs = [f for c in chunks for f in getattr(c, "figure_references", [])]
    detected_figures = len(fig_refs)

    safe_print("\n" + "=" * 72)
    safe_print("  STRUCTURE-AWARE CHUNKING SYSTEM — SUMMARY STATISTICS")
    safe_print("=" * 72)
    safe_print(f"  Total Chunks Generated      : {len(chunks)}")
    safe_print(f"  Average Tokens per Chunk   : {statistics.mean(tokens):.1f}")
    safe_print(f"  Median Tokens per Chunk    : {statistics.median(tokens):.1f}")
    safe_print(f"  Smallest Chunk             : {min(tokens)} tokens")
    safe_print(f"  Largest Chunk              : {max(tokens)} tokens")
    safe_print("-" * 72)
    safe_print("  CHUNKS BY CONTENT TYPE:")
    for c_type, count in type_counts.items():
        safe_print(f"    • {str(c_type):<20} : {count}")
    safe_print("-" * 72)
    safe_print("  CHUNKS BY CHAPTER (TOP 5):")
    for ch, count in chapter_counts.most_common(5):
        safe_print(f"    • {ch[:35]:<35} : {count}")
    safe_print("-" * 72)
    safe_print(f"  Detected & Attached Figures: {detected_figures}")
    safe_print("=" * 72 + "\n")


def run_chunking_evaluation(doc_tree: Any, sample_count: int = 5) -> None:
    """
    Debug evaluation tool: prints detailed preview of sample generated chunks
    (including embedding_text vs content separation and metadata).
    """
    pipeline = ChunkingPipeline()
    chunks = pipeline.run(doc_tree)

    safe_print("\n" + "=" * 72)
    safe_print("  STRUCTURE-AWARE CHUNKING — DEBUG INSPECTION PREVIEW")
    safe_print("=" * 72)
    safe_print(f"Total Chunks: {len(chunks)}\n")

    # Sample representative chunks (Glossary, Table, Paragraph)
    samples = []
    # Pick a glossary chunk
    glos_chunks = [c for c in chunks if c.content_type == ContentType.GLOSSARY_ENTRY]
    if glos_chunks:
        samples.append(("Glossary Entry Chunk", glos_chunks[0]))
    # Pick a table chunk
    tbl_chunks = [c for c in chunks if c.content_type == ContentType.TABLE]
    if tbl_chunks:
        samples.append(("Table Chunk", tbl_chunks[0]))
    # Pick prose chunks
    prose_chunks = [c for c in chunks if c.content_type == ContentType.PARAGRAPH]
    for p in prose_chunks[:min(3, len(prose_chunks))]:
        samples.append(("Prose Chunk", p))

    for label, chunk in samples:
        safe_print("-" * 72)
        safe_print(f"Category     : {label}")
        safe_print(f"Chunk ID     : {chunk.chunk_id}")
        safe_print(f"Content Type : {chunk.content_type}")
        safe_print(f"Page         : {chunk.page_start}")
        safe_print(f"Chapter      : {chunk.chapter}")
        safe_print(f"Section      : {chunk.section}")
        safe_print(f"Title / Term : {chunk.title}")
        safe_print(f"Tokens       : {chunk.token_count}")
        safe_print("\n--- EMBEDDING TEXT (Contextualized Representation) ---")
        safe_print(chunk.embedding_text[:400] + ("..." if len(chunk.embedding_text) > 400 else ""))
        safe_print("\n--- ORIGINAL CONTENT ---")
        safe_print(chunk.content[:300] + ("..." if len(chunk.content) > 300 else ""))
        safe_print("\n")

    print_chunk_statistics(doc_tree, chunks)
    export_chunks(chunks)


if __name__ == "__main__":
    from ingestion.parser import advanced_parse_pdf
    from ingestion.hierarchy_builder import HierarchyBuilder

    PDF_PATH = os.path.join("data", "pdfs", "9789241550284-eng.pdf")
    safe_print(f"[Semantic Chunker CLI] Parsing PDF: {PDF_PATH} ...")
    parsed_docs, _ = advanced_parse_pdf(PDF_PATH)

    builder = HierarchyBuilder()
    doc_tree = builder.build(parsed_docs)

    run_chunking_evaluation(doc_tree)
