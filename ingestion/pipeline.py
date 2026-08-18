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
from ingestion.parser import advanced_parse_pdf
from ingestion.cleaner import clean_text
from ingestion.hierarchy_builder import HierarchyBuilder
from ingestion.chunker import SemanticChunkBuilder, export_chunks
from ingestion.embedder import EmbeddingPipeline
from ingestion.indexer import main as build_index


def run_ingestion(pdf_path: str = os.path.join("data", "pdfs", "9789241550284-eng.pdf")) -> None:
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
    chunks_json_path = os.path.join("data", "chunks", "chunks.json")
    chunks_jsonl_path = os.path.join("data", "chunks", "chunks.jsonl")
    export_chunks(chunks, json_path=chunks_json_path, jsonl_path=chunks_jsonl_path)
    print(f"Generated {len(chunks)} chunks -> {chunks_json_path}")

    # 5. Generate Embeddings
    print("\n[Step 5a/5] Generating vector embeddings via Ollama...")
    embedding_pipeline = EmbeddingPipeline()
    embedding_pipeline.run()

    # 6. Indexing
    print("\n[Step 5b/5] Building FAISS vector index & metadata pickle...")
    build_index()

    print("\n" + "=" * 70)
    print("  INGESTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_ingestion()
