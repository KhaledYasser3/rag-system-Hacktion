"""
=============================================================================
  RETRIEVER FRAMEWORK — Vector Search
=============================================================================
  Performs fast similarity search using FAISS vector store.
  Returns Top-K raw candidate chunks and similarity scores without reranking.
=============================================================================
"""

from __future__ import annotations

import logging
import numpy as np
from typing import List, Tuple, Dict, Any
from config.settings import RetrieverConfig, DEFAULT_CONFIG
from retriever.vector_store import FAISSVectorStore

logger = logging.getLogger("VectorSearch")


class VectorSearchEngine:
    """Similarity search engine over FAISS vector store."""

    def __init__(self, store: FAISSVectorStore, cfg: RetrieverConfig = DEFAULT_CONFIG):
        self.store = store
        self.cfg = cfg

    def search(
        self,
        query_vector: List[float],
        top_k: int | None = None,
        similarity_threshold: float | None = None
    ) -> List[Tuple[dict, float]]:
        """
        Executes vector similarity search against FAISS index.
        Returns list of (chunk_record_dict, similarity_score) tuples.
        """
        if not query_vector or len(query_vector) != self.cfg.embedding_dimension:
            raise ValueError(f"Query vector length mismatch: expected {self.cfg.embedding_dimension}")

        k = top_k or self.cfg.top_k_initial
        threshold = similarity_threshold if similarity_threshold is not None else self.cfg.similarity_threshold

        # Normalize query vector for cosine similarity
        q_np = np.array([query_vector], dtype=np.float32)
        norm = np.linalg.norm(q_np)
        if norm > 0:
            q_np = q_np / norm

        # Execute FAISS search
        scores, indices = self.store.index.search(q_np, min(k, self.store.count()))

        results = []
        if len(indices) > 0:
            for idx, score in zip(indices[0], scores[0]):
                if idx < 0:
                    continue
                sim_score = float(score)
                if sim_score >= threshold:
                    chunk_rec = self.store.get_chunk_by_index(int(idx))
                    results.append((chunk_rec, sim_score))

        logger.debug(f"Vector search returned {len(results)} candidate chunks (top_k={k}, threshold={threshold}).")
        return results
