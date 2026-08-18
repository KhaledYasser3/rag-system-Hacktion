"""
=============================================================================
  RETRIEVER FRAMEWORK — Pipeline Orchestrator (Retrieval Entry Point)
=============================================================================
  Orchestrates query processing, embedding, vector search, reranking, and
  context building without embedding business logic inside the orchestrator.
=============================================================================
"""

from __future__ import annotations

import os
import sys
import time
import logging
from typing import Optional, List

# Ensure project root directory is in Python path for clean script & module execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import RetrieverConfig, DEFAULT_CONFIG
from shared.models import Query, RetrievedChunk, SearchResult
from retriever.prompt_builder import QueryProcessor
from retriever.query_embedder import QueryEmbedder
from retriever.vector_store import FAISSVectorStore
from retriever.search import VectorSearchEngine
from retriever.reranker import BaseReranker, IdentityReranker
from retriever.context_builder import ContextBuilder

logger = logging.getLogger("RetrieverPipeline")


class MedicalRetriever:
    """Production Pipeline Orchestrator for Medical RAG Retrieval."""

    def __init__(
        self,
        cfg: RetrieverConfig = DEFAULT_CONFIG,
        reranker: BaseReranker | None = None
    ):
        self.cfg = cfg
        self.processor = QueryProcessor()
        self.embedder = QueryEmbedder(cfg=cfg)

        # Initialize and load FAISS vector store
        self.vector_store = FAISSVectorStore(cfg=cfg)
        self.vector_store.load_or_build()

        # Search Engine & Reranker
        self.search_engine = VectorSearchEngine(store=self.vector_store, cfg=cfg)
        self.reranker = reranker or IdentityReranker()
        self.context_builder = ContextBuilder(cfg=cfg)

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> SearchResult:
        """
        Orchestrates full retrieval flow:
          Question -> Preprocess -> Embedding -> Search -> Rerank -> ContextBuilder -> SearchResult
        """
        t_start = time.time()
        latencies = {}

        # 1. Preprocess Query
        t0 = time.time()
        query_obj = self.processor.process(question)
        latencies["processing_ms"] = (time.time() - t0) * 1000

        # 2. Generate Query Embedding
        t0 = time.time()
        q_vector = self.embedder.embed_query(query_obj)
        latencies["embedding_ms"] = (time.time() - t0) * 1000

        # 3. Perform Vector Similarity Search
        t0 = time.time()
        initial_k = (top_k or self.cfg.top_k_final) * 4
        candidates = self.search_engine.search(
            query_vector=q_vector,
            top_k=initial_k,
            similarity_threshold=similarity_threshold
        )
        latencies["search_ms"] = (time.time() - t0) * 1000

        # 4. Rerank Candidates
        t0 = time.time()
        reranked_candidates = self.reranker.rerank(query=query_obj, candidates=candidates)
        latencies["rerank_ms"] = (time.time() - t0) * 1000

        # 5. Build Final Context
        t0 = time.time()
        final_chunks = self.context_builder.build_context(
            candidates=reranked_candidates,
            top_k=top_k or self.cfg.top_k_final
        )
        latencies["context_build_ms"] = (time.time() - t0) * 1000

        latencies["total_ms"] = (time.time() - t_start) * 1000

        return SearchResult(
            query=query_obj,
            chunks=final_chunks,
            total_initial_found=len(candidates),
            latency_breakdown_ms=latencies
        )


if __name__ == "__main__":
    import sys
    question = sys.argv[1] if len(sys.argv) > 1 else "What is the recommended second-line treatment for type 2 diabetes?"
    print(f"Executing Medical Retriever for query: '{question}'...")
    retriever = MedicalRetriever()
    result = retriever.retrieve(question)
    print(f"Retrieved {len(result.chunks)} chunks in {result.latency_breakdown_ms.get('total_ms', 0):.2f} ms.")
    for i, c in enumerate(result.chunks, 1):
        print(f"\n[Rank {i} | Score {c.score:.4f} | Page {c.page_start}] {c.content[:200]}...")
