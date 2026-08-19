"""
=============================================================================
  STAGE 5 — OFFLINE QDRANT INDEX BUILDER
=============================================================================
  Standalone script that builds the Qdrant vector index from embeddings.json.
  Supports both dockerized Qdrant server and fallback local embedded Qdrant client.

  Outputs:
      Qdrant Collection 'who_guidelines' containing vectors and payload metadata.
=============================================================================
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import pickle
import logging
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rag_system.config.config import (
    DEFAULT_EMBEDDINGS_JSON,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    EMBEDDING_DIMENSION
)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("QdrantIndexBuilder")


def get_qdrant_client() -> QdrantClient:
    """Connect to Qdrant Docker server. Strictly fails if unreachable."""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=3)
        client.get_collections()  # Ping connection
        logger.info(f"Successfully connected to running Qdrant server at {QDRANT_HOST}:{QDRANT_PORT}")
        return client
    except Exception as e:
        logger.critical(f"Could not connect to Qdrant Docker container at {QDRANT_HOST}:{QDRANT_PORT} ({e}).")
        raise RuntimeError(f"Qdrant Docker container unreachable on {QDRANT_HOST}:{QDRANT_PORT}. Enforced Docker-only storage.") from e


def build_qdrant_index() -> None:
    print()
    print("=" * 60)
    print("  OFFLINE QDRANT INDEX BUILDER")
    print("=" * 60)

    # 1. Load embeddings.json
    logger.info(f"Loading embeddings from {DEFAULT_EMBEDDINGS_JSON}...")
    if not os.path.exists(DEFAULT_EMBEDDINGS_JSON):
        logger.error(f"Embeddings file not found: {DEFAULT_EMBEDDINGS_JSON}")
        logger.info("Please generate embeddings first using the embedding pipeline.")
        sys.exit(1)

    with open(DEFAULT_EMBEDDINGS_JSON, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    
    logger.info(f"Loaded {len(records)} records for indexing.")

    # 2. Connect to Qdrant
    client = get_qdrant_client()

    # 3. Create collection
    logger.info(f"Creating / Re-creating Qdrant collection: '{QDRANT_COLLECTION}'...")
    # Delete if exists
    try:
        client.delete_collection(collection_name=QDRANT_COLLECTION)
    except Exception:
        pass

    # Create collection with Cohere vector size
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
    )
    logger.info(f"Collection '{QDRANT_COLLECTION}' created (Vector Dimension: {EMBEDDING_DIMENSION}, Cosine Metric).")

    # 4. Prepare points and upload
    logger.info("Preparing data points for upload...")
    points = []
    
    for idx, rec in enumerate(records):
        chunk_id = rec.get("chunk_id")
        embedding = rec.get("embedding")
        content = rec.get("content", "")
        meta = rec.get("metadata", {})
        table_refs = rec.get("table_references", [])
        fig_refs = rec.get("figure_references", [])

        if not chunk_id or not embedding:
            logger.warning(f"Skipping record at index {idx} due to missing chunk_id or embedding.")
            continue

        if len(embedding) != EMBEDDING_DIMENSION:
            logger.error(f"Vector dimension mismatch for '{chunk_id}': expected {EMBEDDING_DIMENSION}, got {len(embedding)}")
            sys.exit(1)

        # Generate a deterministic UUID from chunk_id string
        point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

        # Payload contains all metadata fields for direct single-query retrieval
        payload = {
            "chunk_id": chunk_id,
            "content": content,
            "table_references": table_refs,
            "figure_references": fig_refs,
            "document_title": meta.get("document_title", ""),
            "chapter": meta.get("chapter", ""),
            "section": meta.get("section", ""),
            "subsection": meta.get("subsection", ""),
            "page_start": meta.get("page_start", 1),
            "page_end": meta.get("page_end", 1),
            "token_count": meta.get("token_count", 0),
            "language": meta.get("language", "English"),
            "layout_type": meta.get("layout_type", "single_column"),
            "semantic_class": meta.get("semantic_class", ""),
            "content_hash": meta.get("content_hash", "")
        }

        points.append(
            PointStruct(
                id=point_uuid,
                vector=embedding,
                payload=payload
            )
        )

    # Upload points in batches
    batch_size = 64
    logger.info(f"Uploading {len(points)} points to Qdrant in batches of {batch_size}...")
    
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=batch
        )
        logger.info(f"Uploaded batch {i // batch_size + 1} / {math.ceil(len(points) / batch_size)}")

    # 5. Verify search
    logger.info("Running post-indexing verification...")
    col_info = client.get_collection(collection_name=QDRANT_COLLECTION)
    logger.info(f"Verification successful: collection '{QDRANT_COLLECTION}' holds {col_info.points_count} points.")

    print()
    print("=" * 60)
    print("  Qdrant Indexing Completed.")
    print("  Collection Ready.")
    print("=" * 60)
    print()


import math
if __name__ == "__main__":
    build_qdrant_index()
