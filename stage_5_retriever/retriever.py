"""
=============================================================================
  STAGE 5: RETRIEVER FRAMEWORK — Pipeline Orchestrator
=============================================================================
  Orchestrates query processing, embedding, vector search, reranking, and
  context building without embedding business logic inside the orchestrator.
=============================================================================
"""

from __future__ import annotations

import time
import logging
from typing import Optional, List
from stage_5_retriever.config import RetrieverConfig, DEFAULT_CONFIG
from stage_5_retriever.models import Query, RetrievedChunk, SearchResult
from stage_5_retriever.query_processor import QueryProcessor
from stage_5_retriever.query_embedder import QueryEmbedder
from stage_5_retriever.vector_store import FAISSVectorStore
from stage_5_retriever.vector_search import VectorSearchEngine
from stage_5_retriever.reranker import BaseReranker, IdentityReranker
from stage_5_retriever.context_builder import ContextBuilder

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
