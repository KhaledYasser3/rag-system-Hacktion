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
