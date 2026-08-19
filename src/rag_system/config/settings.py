"""
=============================================================================
  CONFIGURATION MODULE
=============================================================================
  Centralized settings and hyperparameters for vector indexing, query
  processing, FAISS similarity search, reranking, and context building.
=============================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple
from rag_system.config.config import BASE_DIR


@dataclass
class RetrieverConfig:
    """Centralized configuration parameters for Retriever Framework."""

    # Embedding Model & Server Settings
    embedding_model: str = "embed-multilingual-v3.0"
    embedding_dimension: int = 1024

    # Qdrant Server Settings
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "who_guidelines"

    # Paths
    embeddings_json_path: str = os.path.join(BASE_DIR, "data", "embeddings", "embeddings.json")
    chunks_json_path: str = os.path.join(BASE_DIR, "data", "chunks", "chunks.json")

    # Search & Retrieval Hyperparameters
    top_k_initial: int = 20           # Initial candidate retrieval count from Qdrant
    top_k_final: int = 5              # Final candidate count after reranking & context building
    similarity_threshold: float = 0.30   # Minimum inner-product / cosine similarity score
    distance_metric: str = "cosine"   # "cosine", "inner_product", or "l2"

    # Context Building & Budgeting
    max_context_tokens: int = 2000    # Maximum token cap for final retrieved context window
    sort_by_page: bool = True         # Sort final output chunks by PDF page order if True

    # Network Timeouts & Retries
    query_timeout_seconds: int = 15
    max_retries: int = 3
    retry_delays: Tuple[int, ...] = (1, 2, 4)

    # Logging
    log_level: str = "INFO"


# Global default configuration instance
DEFAULT_CONFIG = RetrieverConfig()

