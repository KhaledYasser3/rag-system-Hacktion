"""
=============================================================================
  STAGE 5A — OFFLINE INDEX BUILDER
=============================================================================
  Standalone script that builds the FAISS vector index and metadata store
  from embeddings.json.

  Run this ONCE whenever embeddings.json changes:

      python build_faiss_index.py

  Outputs:
      vector_index.faiss  -- FAISS IndexFlatIP (L2-normalized, cosine sim)
      metadata.pkl        -- List[dict] containing chunk payload WITHOUT embeddings

  This script is NEVER invoked during retrieval.
=============================================================================
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import sys
from typing import List, Dict, Any

import faiss
import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("IndexBuilder")

# ---------------------------------------------------------------------------
# Constants -- mirror RetrieverConfig defaults
# ---------------------------------------------------------------------------
EMBEDDINGS_JSON_PATH: str = "embeddings.json"
VECTOR_INDEX_PATH: str = "vector_index.faiss"
METADATA_PKL_PATH: str = "metadata.pkl"
EXPECTED_DIMENSION: int = 768

# Payload fields to keep in metadata (embeddings are intentionally excluded)
METADATA_FIELDS = ("chunk_id", "content", "metadata", "table_references", "figure_references")


# ---------------------------------------------------------------------------
# Step 1: Load & validate embeddings.json
# ---------------------------------------------------------------------------

def _load_embeddings(path: str) -> List[Dict[str, Any]]:
    """Load embeddings.json and perform basic structural validation."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"embeddings.json not found at '{path}'.\n"
            "Run the Stage 4 embedding generator first:\n"
            "    python generate_embeddings.py"
        )
    with open(path, "r", encoding="utf-8") as fh:
        records = json.load(fh)

    if not isinstance(records, list) or len(records) == 0:
        raise ValueError(f"'{path}' is empty or not a list.")

    logger.info(f"Loaded {len(records)} records from '{path}'.")
    return records


# ---------------------------------------------------------------------------
# Step 2: Validate individual records
# ---------------------------------------------------------------------------

def _validate_records(records: List[Dict[str, Any]]) -> None:
    """Validate every record -- abort on first structural error."""
    seen_ids: set = set()
    for i, rec in enumerate(records):
        cid = rec.get("chunk_id", "")
        if not cid:
            raise ValueError(f"Record[{i}] is missing 'chunk_id'.")
        if cid in seen_ids:
            raise ValueError(f"Duplicate chunk_id detected: '{cid}'.")
        seen_ids.add(cid)

        vec = rec.get("embedding", [])
        if not vec:
            raise ValueError(f"Record '{cid}' has an empty embedding vector.")
        if len(vec) != EXPECTED_DIMENSION:
            raise ValueError(
                f"Record '{cid}' has wrong dimension: expected {EXPECTED_DIMENSION}, got {len(vec)}."
            )
        vec_np = np.array(vec, dtype=np.float32)
        if np.any(np.isnan(vec_np)) or np.any(np.isinf(vec_np)):
            raise ValueError(f"Record '{cid}' contains NaN or Inf in embedding vector.")


# ---------------------------------------------------------------------------
# Step 3: Build L2-normalized vector matrix
# ---------------------------------------------------------------------------

def _build_matrix(records: List[Dict[str, Any]]) -> np.ndarray:
    """Extract, stack, and L2-normalize embedding vectors."""
    matrix = np.array([rec["embedding"] for rec in records], dtype=np.float32)
    logger.info(f"Vector matrix shape: {matrix.shape}  (dtype={matrix.dtype})")

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms < 1e-10] = 1e-10
    normalized = matrix / norms
    logger.info("Vectors L2-normalized successfully.")
    return normalized


# ---------------------------------------------------------------------------
# Step 4: Build & persist FAISS index
# ---------------------------------------------------------------------------

def _build_and_save_index(normalized_matrix: np.ndarray, out_path: str) -> faiss.IndexFlatIP:
    """Create IndexFlatIP, add vectors, and persist to disk."""
    dim = normalized_matrix.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(normalized_matrix)
    faiss.write_index(index, out_path)
    logger.info(f"FAISS index saved -> '{out_path}'  ({index.ntotal} vectors, dim={dim})")
    return index


# ---------------------------------------------------------------------------
# Step 5: Strip embeddings and persist metadata
# ---------------------------------------------------------------------------

def _save_metadata(records: List[Dict[str, Any]], out_path: str) -> List[Dict[str, Any]]:
    """
    Persist only chunk payload fields (chunk_id, content, metadata,
    table_references, figure_references).
    The 'embedding' key is intentionally excluded to avoid duplicate storage.
    """
    payloads = []
    for rec in records:
        payload = {field: rec.get(field) for field in METADATA_FIELDS}
        payloads.append(payload)

    with open(out_path, "wb") as fh:
        pickle.dump(payloads, fh, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info(f"Metadata saved -> '{out_path}'  ({len(payloads)} records, embeddings excluded)")
    return payloads


# ---------------------------------------------------------------------------
# Step 6: Post-build cross-validation
# ---------------------------------------------------------------------------

def _validate_outputs(
    index: faiss.IndexFlatIP,
    payloads: List[Dict[str, Any]],
) -> None:
    """Cross-validate FAISS index vs metadata after build."""
    errors: List[str] = []

    if index.ntotal != len(payloads):
        errors.append(
            f"Count mismatch: FAISS has {index.ntotal} vectors "
            f"but metadata has {len(payloads)} records."
        )

    if index.d != EXPECTED_DIMENSION:
        errors.append(
            f"Dimension mismatch: FAISS index is {index.d}-dim, "
            f"expected {EXPECTED_DIMENSION}."
        )

    chunk_ids = [p.get("chunk_id") for p in payloads]
    if len(chunk_ids) != len(set(chunk_ids)):
        errors.append("Duplicate chunk_ids found in saved metadata.")

    missing_content = [p.get("chunk_id") for p in payloads if not p.get("content")]
    if missing_content:
        errors.append(f"Records with missing content: {missing_content[:5]}")

    if errors:
        for err in errors:
            logger.error("  FAIL: %s", err)
        raise RuntimeError("Post-build validation FAILED. Index is NOT usable.")

    print(f"  [OK] index dimension       : {index.d}")
    print(f"  [OK] vector count          : {index.ntotal}")
    print(f"  [OK] metadata count        : {len(payloads)}")
    print(f"  [OK] duplicate chunk_ids   : 0")
    print(f"  [OK] missing content       : 0")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print("=" * 60)
    print("  OFFLINE FAISS INDEX BUILDER")
    print("=" * 60)

    print(f"\nLoading {EMBEDDINGS_JSON_PATH}...")
    records = _load_embeddings(EMBEDDINGS_JSON_PATH)
    print(f"Loaded {len(records)} vectors.")

    print("Validating records...")
    _validate_records(records)
    print("Validation passed.")

    print("Normalizing vectors...")
    normalized = _build_matrix(records)

    print("Building FAISS index...")
    index = _build_and_save_index(normalized, VECTOR_INDEX_PATH)
    print(f"Saving {VECTOR_INDEX_PATH}...")

    print(f"Saving {METADATA_PKL_PATH}...")
    payloads = _save_metadata(records, METADATA_PKL_PATH)

    print("\nRunning post-build validation...")
    _validate_outputs(index, payloads)

    print()
    print("=" * 60)
    print("  Validation Passed.")
    print("  Index Ready.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
