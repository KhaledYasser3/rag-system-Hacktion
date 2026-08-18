"""
=============================================================================
  RETRIEVER FRAMEWORK -- Vector Store (LOAD-ONLY)
=============================================================================
  Loads a pre-built FAISS index (vector_index.faiss) and its companion
  metadata store (metadata.pkl).
=============================================================================
"""

from __future__ import annotations

import logging
import os
import pickle
from abc import ABC, abstractmethod
from typing import List

import faiss

from config.settings import RetrieverConfig, DEFAULT_CONFIG

logger = logging.getLogger("VectorStore")


class BaseVectorStore(ABC):
    """Abstract contract for all vector database backends."""

    @abstractmethod
    def load_or_build(self) -> None:
        """
        Load the pre-built index from disk.
        Implementations MUST NOT build or rebuild the index here.
        """
        pass

    @abstractmethod
    def get_chunk_by_index(self, idx: int) -> dict:
        """Return the full chunk payload dict for a given FAISS index position."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return the total number of vectors in the loaded index."""
        pass


class FAISSVectorStore(BaseVectorStore):
    """
    Production FAISS vector store.
    """

    def __init__(self, cfg: RetrieverConfig = DEFAULT_CONFIG) -> None:
        self.cfg = cfg
        self.index: faiss.IndexFlatIP | None = None
        self.records: List[dict] = []
        self.dim: int = cfg.embedding_dimension

    def load_or_build(self) -> None:
        """Load pre-built FAISS index and metadata from disk."""
        self._load_faiss_index()
        self._load_metadata()
        self._validate_store()
        logger.info(
            "VectorStore ready: %d vectors (dim=%d)", self.index.ntotal, self.index.d
        )

    def get_chunk_by_index(self, idx: int) -> dict:
        """Return raw payload record for a given FAISS position."""
        if 0 <= idx < len(self.records):
            return self.records[idx]
        raise IndexError(
            f"Index {idx} is out of range [0, {len(self.records)})."
        )

    def count(self) -> int:
        """Return total vector count inside loaded FAISS index."""
        return self.index.ntotal if self.index is not None else 0

    def _load_faiss_index(self) -> None:
        """Read persisted FAISS index from disk."""
        path = self.cfg.vector_index_path
        if not os.path.exists(path):
            raise RuntimeError(
                f"\n[VectorStore] FAISS index not found: '{path}'\n\n"
                "The index must be built before starting the retriever.\n"
                "Run the ingestion pipeline or index builder first:\n\n"
                "    python -m ingestion.pipeline\n"
            )
        self.index = faiss.read_index(path)
        logger.info("FAISS index loaded from '%s' (%d vectors, dim=%d)",
                    path, self.index.ntotal, self.index.d)

    def _load_metadata(self) -> None:
        """Load chunk payload store from pickle file."""
        path = self.cfg.metadata_pkl_path
        if not os.path.exists(path):
            raise RuntimeError(
                f"\n[VectorStore] Metadata store not found: '{path}'\n\n"
                "Rebuild by running:\n\n"
                "    python -m ingestion.pipeline\n"
            )
        with open(path, "rb") as fh:
            self.records = pickle.load(fh)
        logger.info("Metadata loaded from '%s' (%d records)", path, len(self.records))

    def _validate_store(self) -> None:
        """Cross-validate FAISS index and metadata after loading."""
        errors: List[str] = []

        if self.index.ntotal != len(self.records):
            errors.append(
                f"Count mismatch: FAISS has {self.index.ntotal} vectors "
                f"but metadata has {len(self.records)} records."
            )

        if self.index.d != self.dim:
            errors.append(
                f"Dimension mismatch: FAISS index is {self.index.d}-dim, "
                f"config expects {self.dim}-dim."
            )

        chunk_ids = [r.get("chunk_id") for r in self.records]
        duplicate_ids = [cid for cid in chunk_ids if chunk_ids.count(cid) > 1]
        if duplicate_ids:
            errors.append(
                f"Duplicate chunk_ids in metadata: {list(set(duplicate_ids))[:5]}"
            )

        missing_content = [r.get("chunk_id") for r in self.records if not r.get("content")]
        if missing_content:
            errors.append(
                f"Records with missing content field: {missing_content[:5]}"
            )

        if errors:
            for err in errors:
                logger.error(" [FAIL] %s", err)
            raise RuntimeError(
                "VectorStore startup validation FAILED:\n - "
                + "\n - ".join(errors)
            )

        logger.info("Store validation passed.")
