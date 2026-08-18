"""
Global environment configuration parameters.
"""

import os

# Project root path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default Data Paths
PDF_DIR = os.path.join(BASE_DIR, "data", "pdfs")
DEFAULT_PDF_PATH = os.path.join(PDF_DIR, "9789241550284-eng.pdf")

CHUNKS_DIR = os.path.join(BASE_DIR, "data", "chunks")
DEFAULT_CHUNKS_JSON = os.path.join(CHUNKS_DIR, "chunks.json")
DEFAULT_CHUNKS_JSONL = os.path.join(CHUNKS_DIR, "chunks.jsonl")

EMBEDDINGS_DIR = os.path.join(BASE_DIR, "data", "embeddings")
DEFAULT_EMBEDDINGS_JSON = os.path.join(EMBEDDINGS_DIR, "embeddings.json")

VECTOR_DB_DIR = os.path.join(BASE_DIR, "data", "vector_db")
DEFAULT_VECTOR_INDEX = os.path.join(VECTOR_DB_DIR, "vector_index.faiss")
DEFAULT_METADATA_PKL = os.path.join(VECTOR_DB_DIR, "metadata.pkl")

# Ollama Host & Embedding model defaults
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
