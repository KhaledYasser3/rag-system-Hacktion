"""
=============================================================================
  RETRIEVER FRAMEWORK — Qdrant Similarity Search
=============================================================================
  Performs similarity search against Qdrant collection.
  Returns Top-K raw candidate chunks and similarity scores without reranking.
=============================================================================
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any
from rag_system.config.settings import RetrieverConfig, DEFAULT_CONFIG
from rag_system.retriever.vector_store import QdrantVectorStore

logger = logging.getLogger("QdrantSearchEngine")


class VectorSearchEngine:
    """Similarity search engine over Qdrant vector database."""

    def __init__(self, store: QdrantVectorStore, cfg: RetrieverConfig = DEFAULT_CONFIG):
        self.store = store
        self.cfg = cfg

    def search(
        self,
        query_vector: List[float],
        top_k: int | None = None,
        similarity_threshold: float | None = None
    ) -> List[Tuple[dict, float]]:
        """
        Executes vector similarity search against Qdrant collection.
        Returns list of (chunk_record_payload_dict, similarity_score) tuples.
        """
        if not self.store.client:
            raise RuntimeError("QdrantVectorStore is not initialized.")

        if not query_vector or len(query_vector) != self.cfg.embedding_dimension:
            raise ValueError(f"Query vector length mismatch: expected {self.cfg.embedding_dimension}")

        k = top_k or self.cfg.top_k_initial
        threshold = similarity_threshold if similarity_threshold is not None else self.cfg.similarity_threshold

        # Execute search in Qdrant collection
        try:
            if hasattr(self.store.client, "query_points"):
                response = self.store.client.query_points(
                    collection_name=self.cfg.qdrant_collection,
                    query=query_vector,
                    limit=k,
                    score_threshold=threshold
                )
                hits = response.points
            else:
                hits = self.store.client.search(
                    collection_name=self.cfg.qdrant_collection,
                    query_vector=query_vector,
                    limit=k,
                    score_threshold=threshold
                )
            
            results = []
            for hit in hits:
                # hit.payload contains metadata + content + table/figure references
                payload = hit.payload
                # Add score into the payload dict if needed
                results.append((payload, float(hit.score)))
                
            logger.info(f"Qdrant vector search returned {len(results)} candidate chunks (top_k={k}, threshold={threshold}).")
            return results

            
        except Exception as e:
            logger.error(f"Search failed in Qdrant collection '{self.cfg.qdrant_collection}': {e}")
            raise RuntimeError(f"Qdrant vector search failed: {e}") from e
