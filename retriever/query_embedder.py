"""
=============================================================================
  RETRIEVER FRAMEWORK — Query Embedder
=============================================================================
  Generates 768-dimensional query vector embeddings using local Ollama
  (nomic-embed-text) with exponential retries and error handling.
=============================================================================
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
import logging
from typing import List, Union, Optional
from config.settings import RetrieverConfig, DEFAULT_CONFIG
from shared.models import Query

logger = logging.getLogger("QueryEmbedder")


class QueryEmbedder:
    """Query embedding generator connected to local Ollama instance."""

    def __init__(self, cfg: RetrieverConfig = DEFAULT_CONFIG):
        self.cfg = cfg
        self.host = cfg.ollama_host.rstrip("/")
        self.model = cfg.embedding_model

    def embed_query(self, query: Union[str, Query]) -> List[float]:
        """
        Generates 768-dimensional embedding vector for query string or Query model.
        Returns L2-normalized float list.
        """
        q_text = query.processed_query if isinstance(query, Query) else str(query).strip()
        if not q_text:
            raise ValueError("Query text cannot be empty for embedding generation.")

        # Construct embedding prompt
        formatted_prompt = f"search_query: {q_text}"

        url = f"{self.host}/api/embeddings"
        payload = json.dumps({
            "model": self.model,
            "prompt": formatted_prompt
        }).encode("utf-8")

        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=self.cfg.query_timeout_seconds) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    embedding = res.get("embedding", [])
                    if embedding and len(embedding) == self.cfg.embedding_dimension:
                        if isinstance(query, Query):
                            query.embedding = embedding
                        return embedding
                    else:
                        logger.warning(
                            f"Query embedding returned invalid dimension ({len(embedding)} vs expected {self.cfg.embedding_dimension})"
                        )
            except Exception as e:
                delay = self.cfg.retry_delays[min(attempt - 1, len(self.cfg.retry_delays) - 1)]
                logger.warning(f"Query embedding request attempt {attempt}/{self.cfg.max_retries} failed ({e}). Retrying in {delay}s...")
                time.sleep(delay)

        raise RuntimeError(f"Failed to generate query embedding from Ollama after {self.cfg.max_retries} attempts.")
