"""
=============================================================================
  STAGE 5: RETRIEVER FRAMEWORK — Configuration Module
=============================================================================
  Centralized settings and hyperparameters for vector indexing, query
  processing, FAISS similarity search, reranking, and context building.
=============================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple


@dataclass
class RetrieverConfig:
    """Centralized configuration parameters for Stage 5 Retriever Framework."""

    # Embedding Model & Server Settings
    embedding_model: str = "nomic-embed-text"
    ollama_host: str = "http://localhost:11434"
    embedding_dimension: int = 768

    # Paths
    embeddings_json_path: str = "embeddings.json"
    chunks_json_path: str = "chunks.json"
    vector_index_path: str = "vector_index.faiss"

    # Search & Retrieval Hyperparameters
    top_k_initial: int = 20           # Initial candidate retrieval count from FAISS
    top_k_final: int = 5              # Final candidate count after reranking & context building
    similarity_threshold: float = 0.30   # Minimum inner-product / cosine similarity score
    distance_metric: str = "cosine"   # "cosine", "inner_product", or "l2"

    # Context Building & Budgeting
    max_context_tokens: int = 2000    # Maximum token cap for final retrieved context window
    sort_by_page: bool = False        # Sort final output chunks by PDF page order if True

    # Network Timeouts & Retries
    query_timeout_seconds: int = 15
    max_retries: int = 3
    retry_delays: Tuple[int, ...] = (1, 2, 4)

    # Logging
    log_level: str = "INFO"


# Global default configuration instance
DEFAULT_CONFIG = RetrieverConfig()
