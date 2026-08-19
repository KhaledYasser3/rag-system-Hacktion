"""
=============================================================================
  RETRIEVER FRAMEWORK — Reranker Module
=============================================================================
  Defines abstract Reranker interface and Identity Reranker implementation.
  Supports future integration of CrossEncoders, BGE Reranker, or Jina Reranker.
=============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple
from rag_system.shared.models import Query


class BaseReranker(ABC):
    """Abstract interface for chunk rerankers (Identity, CrossEncoder, BGE)."""

    @abstractmethod
    def rerank(
        self,
        query: Query,
        candidates: List[Tuple[dict, float]]
    ) -> List[Tuple[dict, float]]:
        """Reranks list of (chunk_dict, float_score) tuples based on query relevance."""
        pass


class IdentityReranker(BaseReranker):
    """Pass-through reranker preserving original vector store similarity ranking."""

    def rerank(
        self,
        query: Query,
        candidates: List[Tuple[dict, float]]
    ) -> List[Tuple[dict, float]]:
        """Returns candidates sorted by initial vector similarity score descending."""
        return sorted(candidates, key=lambda x: x[1], reverse=True)


class CrossEncoderReranker(BaseReranker):
    """Extensible placeholder for CrossEncoder / BGE / Jina deep learning rerankers."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        self.model_name = model_name

    def rerank(
        self,
        query: Query,
        candidates: List[Tuple[dict, float]]
    ) -> List[Tuple[dict, float]]:
        """Hook for neural cross-encoder scoring. Defaults to vector ranking if model uninitialized."""
        return sorted(candidates, key=lambda x: x[1], reverse=True)


class CohereReranker(BaseReranker):
    """Neural Reranker using Cohere's rerank API (rerank-multilingual-v3.0)."""

    def __init__(self, api_key: str | None = None, model: str = "rerank-multilingual-v3.0"):
        import os
        self.model = model
        self.api_key = api_key or os.environ.get("COHERE_API_KEY", "").strip()
        self.client = None
        if self.api_key:
            try:
                import cohere
                self.client = cohere.Client(api_key=self.api_key)
            except ImportError:
                pass

    def rerank(
        self,
        query: Query,
        candidates: List[Tuple[dict, float]]
    ) -> List[Tuple[dict, float]]:
        if not self.client or not candidates:
            return sorted(candidates, key=lambda x: x[1], reverse=True)
            
        try:
            # Format documents for Cohere Rerank API
            docs = [c[0]["content"] for c in candidates]
            response = self.client.rerank(
                query=query.processed_query,
                documents=docs,
                top_n=len(candidates),
                model=self.model
            )
            
            # Map rerank results back to original candidates
            reranked = []
            for result in response.results:
                orig_candidate = candidates[result.index]
                # Combine original metadata with new rerank score
                reranked.append((orig_candidate[0], float(result.relevance_score)))
            return reranked
        except Exception:
            # Fallback to original vector similarity order if API fails
            return sorted(candidates, key=lambda x: x[1], reverse=True)
