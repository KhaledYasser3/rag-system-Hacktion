"""
=============================================================================
  INGESTION PIPELINE ORCHESTRATOR
=============================================================================
  Orchestrates all document ingestion stages in order:
  Parse -> Clean -> Build Hierarchy -> Chunk -> Embed -> Index
=============================================================================
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rag_system.ingestion.parser import advanced_parse_pdf
from rag_system.ingestion.cleaner import clean_text
from rag_system.ingestion.hierarchy_builder import HierarchyBuilder
from rag_system.ingestion.chunker import SemanticChunkBuilder, export_chunks
from rag_system.ingestion.embedder import EmbeddingPipeline
from rag_system.ingestion.indexer import build_qdrant_index as build_index
from rag_system.config.config import DEFAULT_PDF_PATH, DEFAULT_CHUNKS_JSON, DEFAULT_CHUNKS_JSONL


def run_ingestion(pdf_path: str = DEFAULT_PDF_PATH) -> None:
    """
    Executes the full ingestion pipeline end-to-end.
    """
    print("=" * 70)
    print("  STARTING DOCUMENT INGESTION PIPELINE")
    print("=" * 70)

    # 1. Parse PDF
    print(f"\n[Step 1/5] Parsing PDF document: {pdf_path}...")
    parsed_docs, tracker = advanced_parse_pdf(pdf_path)
    if not parsed_docs:
        raise RuntimeError(f"Parsing failed for PDF file: {pdf_path}")
    print(f"Parsed {len(parsed_docs)} pages successfully.")

    # 2. Clean Text
    print("\n[Step 2/5] Cleaning text contents...")
    for doc in parsed_docs:
        if "content" in doc and doc["content"]:
            doc["content"] = clean_text(doc["content"])

    # 3. Build Hierarchy
    print("\n[Step 3/5] Building semantic document hierarchy...")
    hierarchy_builder = HierarchyBuilder()
    doc_tree = hierarchy_builder.build(parsed_docs)

    # 4. Chunk Document
    print("\n[Step 4/5] Constructing semantic chunks...")
    chunk_builder = SemanticChunkBuilder(
        min_chunk_tokens=150,
        target_chunk_tokens=450,
        max_chunk_tokens=800
    )
    chunks = chunk_builder.build_chunks(doc_tree)
    export_chunks(chunks, json_path=DEFAULT_CHUNKS_JSON, jsonl_path=DEFAULT_CHUNKS_JSONL)
    print(f"Generated {len(chunks)} chunks -> {DEFAULT_CHUNKS_JSON}")

    # 5. Generate Embeddings
    print("\n[Step 5a/5] Generating vector embeddings via Cohere API...")
    embedding_pipeline = EmbeddingPipeline()
    embedding_pipeline.run()

    # 6. Indexing
    print("\n[Step 5b/5] Building Qdrant collection & indexing...")
    build_index()

    print("\n" + "=" * 70)
    print("  INGESTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_ingestion()

