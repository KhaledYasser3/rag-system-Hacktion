"""
Global environment configuration parameters.
"""

import os
from dotenv import load_dotenv

# Project root path (absolute path to rag-system/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Load .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))


# Default Data Paths
PDF_DIR = os.path.join(BASE_DIR, "data") # data is in workspace root
DEFAULT_PDF_PATH = os.path.join(PDF_DIR, "9789241550284-eng.pdf")

CHUNKS_DIR = os.path.join(BASE_DIR, "data", "chunks")
DEFAULT_CHUNKS_JSON = os.path.join(CHUNKS_DIR, "chunks.json")
DEFAULT_CHUNKS_JSONL = os.path.join(CHUNKS_DIR, "chunks.jsonl")

EMBEDDINGS_DIR = os.path.join(BASE_DIR, "data", "embeddings")
DEFAULT_EMBEDDINGS_JSON = os.path.join(EMBEDDINGS_DIR, "embeddings.json")

# Qdrant configuration parameters
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "who_guidelines"
QDRANT_LOCAL_PATH = os.path.join(BASE_DIR, "data", "qdrant_db")

# Cohere API configuration
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")
COHERE_EMBED_MODEL = "embed-multilingual-v3.0"
EMBEDDING_DIMENSION = 1024  # Cohere Multilingual v3.0 dimension size

# Ollama Host & Embedding model defaults (keep as fallback)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

