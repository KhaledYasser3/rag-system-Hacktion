"""
=============================================================================
  STAGE 5: RETRIEVER FRAMEWORK — Vector Store
=============================================================================
  Abstract Vector Store interface and FAISS implementation for loading
  vector indices and chunk payloads.
=============================================================================
"""

from __future__ import annotations

import os
import json
import logging
import numpy as np
import faiss
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from stage_5_retriever.config import RetrieverConfig, DEFAULT_CONFIG

logger = logging.getLogger("VectorStore")


class BaseVectorStore(ABC):
    """Abstract interface for Vector Database stores (FAISS, Chroma, Qdrant)."""

    @abstractmethod
    def load_or_build(self) -> None:
        """Loads existing index from disk or builds index from embeddings.json."""
        pass

    @abstractmethod
    def get_chunk_by_index(self, idx: int) -> dict:
        """Returns full chunk record dictionary by index position."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Returns total number of indexed vectors."""
        pass


class FAISSVectorStore(BaseVectorStore):
    """FAISS-based Vector Store using inner-product (cosine) similarity indexing."""

    def __init__(self, cfg: RetrieverConfig = DEFAULT_CONFIG):
        self.cfg = cfg
        self.index: faiss.IndexFlatIP | None = None
        self.records: List[dict] = []
        self.dim: int = cfg.embedding_dimension

    def load_or_build(self) -> None:
        """Loads FAISS index from disk or builds new index from embeddings.json."""
        if not os.path.exists(self.cfg.embeddings_json_path):
            raise FileNotFoundError(f"Embeddings file not found: {self.cfg.embeddings_json_path}")

        logger.info(f"Loading vector records from {self.cfg.embeddings_json_path}...")
        with open(self.cfg.embeddings_json_path, "r", encoding="utf-8") as f:
            self.records = json.load(f)

        if not self.records:
            raise ValueError("embeddings.json is empty!")

        # Extract embeddings matrix
        raw_matrix = []
        for r in self.records:
            vec = r.get("embedding", [])
            if not vec or len(vec) != self.dim:
                raise ValueError(f"Vector length mismatch for chunk '{r.get('chunk_id')}': expected {self.dim}, got {len(vec)}")
            raw_matrix.append(vec)

        matrix_np = np.array(raw_matrix, dtype=np.float32)

        # L2-normalize vectors for exact Cosine Similarity via Inner Product
        norms = np.linalg.norm(matrix_np, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        normalized_matrix = matrix_np / norms

        # Create FAISS IndexFlatIP
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(normalized_matrix)

        # Save index to disk if path configured
        try:
            faiss.write_index(self.index, self.cfg.vector_index_path)
            logger.info(f"FAISS vector index built successfully: {self.count()} vectors (Dim: {self.dim}) saved to {self.cfg.vector_index_path}")
        except Exception as e:
            logger.warning(f"Could not save FAISS index to {self.cfg.vector_index_path}: {e}")

    def get_chunk_by_index(self, idx: int) -> dict:
        """Returns raw payload record dictionary for vector index position."""
        if 0 <= idx < len(self.records):
            return self.records[idx]
        raise IndexError(f"Vector index {idx} out of range [0, {len(self.records)})")

    def count(self) -> int:
        """Returns total vector count in index."""
        return self.index.ntotal if self.index else 0
