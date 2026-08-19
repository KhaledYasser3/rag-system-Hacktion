"""
=============================================================================
  RETRIEVER FRAMEWORK -- Qdrant Vector Store
=============================================================================
  Loads or connects to a Qdrant collection ('who_guidelines').
  Supports Docker server connection with automatic fallback to local disk DB.
=============================================================================
"""

from __future__ import annotations

import os
import sys
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from qdrant_client import QdrantClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rag_system.config.settings import RetrieverConfig, DEFAULT_CONFIG

logger = logging.getLogger("QdrantVectorStore")


class BaseVectorStore(ABC):
    """Abstract contract for all vector database backends."""

    @abstractmethod
    def load_or_build(self) -> None:
        """Load the pre-built index or connect to database."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return the total number of vectors in the database."""
        pass


class QdrantVectorStore(BaseVectorStore):
    """
    Production Qdrant Vector Store client.
    Supports both dockerized Qdrant host and local disk-based embedded storage.
    """

    def __init__(self, cfg: RetrieverConfig = DEFAULT_CONFIG) -> None:
        self.cfg = cfg
        self.client: QdrantClient | None = None
        self.collection_name = cfg.qdrant_collection
        self.is_embedded = False

    def load_or_build(self) -> None:
        """Initialize connection to Qdrant Docker server. Strictly fails if unreachable."""
        try:
            self.client = QdrantClient(host=self.cfg.qdrant_host, port=self.cfg.qdrant_port, timeout=3)
            self.client.get_collections()  # Ping server
            self.is_embedded = False
            logger.info(f"Connected to Qdrant server at {self.cfg.qdrant_host}:{self.cfg.qdrant_port}")
        except Exception as e:
            logger.critical(f"Qdrant docker container unreachable on {self.cfg.qdrant_host}:{self.cfg.qdrant_port} ({e}).")
            raise RuntimeError(f"Qdrant Docker container unreachable on {self.cfg.qdrant_host}:{self.cfg.qdrant_port}. Enforced Docker-only storage.") from e

        # 3. Verify collection exists
        try:
            col_info = self.client.get_collection(collection_name=self.collection_name)
            logger.info(f"Connected to Qdrant collection: '{self.collection_name}' (Points count: {col_info.points_count})")
        except Exception as e:
            logger.critical(f"Collection '{self.collection_name}' not found in Qdrant database! {e}")
            logger.info("Please run the ingestion pipeline first to build the index: `python -m src.ingestion.pipeline`")

    def count(self) -> int:
        """Return total vector count inside Qdrant collection."""
        if not self.client:
            return 0
        try:
            col_info = self.client.get_collection(collection_name=self.collection_name)
            return col_info.points_count
        except Exception:
            return 0
