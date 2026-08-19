"""
=============================================================================
  RETRIEVER FRAMEWORK — Query Embedder
=============================================================================
  Generates query vector embeddings using the BaseEmbedder concrete subclasses.
  Automatically selects CohereEmbedder if API key is present, fallback to local.
=============================================================================
"""

from __future__ import annotations

import os
import sys
import logging
from typing import List, Union

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rag_system.config.settings import RetrieverConfig, DEFAULT_CONFIG
from rag_system.shared.models import Query
from rag_system.embeddings import BaseEmbedder, CohereEmbedder, FastEmbedEmbedder, OllamaEmbedder

logger = logging.getLogger("QueryEmbedder")


class QueryEmbedder:
    """Wrapper query embedder selecting Cohere, FastEmbed, or Ollama backend."""

    def __init__(self, cfg: RetrieverConfig = DEFAULT_CONFIG, api_key: str | None = None):
        self.cfg = cfg
        
        # Load API key prioritizing passed arg, then env vars
        cohere_key = api_key or os.environ.get("COHERE_API_KEY", "").strip()
        
        if cohere_key:
            logger.info(f"QueryEmbedder using CohereEmbedder (Model: {cfg.embedding_model}).")
            self.embedder = CohereEmbedder(api_key=cohere_key, model=cfg.embedding_model)
        else:
            logger.warning("COHERE_API_KEY not found. QueryEmbedder falling back to local FastEmbed (BAAI/bge-small-en-v1.5)...")
            self.embedder = FastEmbedEmbedder()

    def embed_query(self, query: Union[str, Query]) -> List[float]:
        """Generates embedding vector for a Query object or a plain string."""
        q_text = query.processed_query if isinstance(query, Query) else str(query).strip()
        if not q_text:
            raise ValueError("Query text cannot be empty.")

        # Construct embedding search query format
        embedding = self.embedder.embed_query(q_text)
        
        if isinstance(query, Query):
            query.embedding = embedding
            
        return embedding
