"""
Custom exception classes for the Medical RAG system.
"""

class RAGBaseException(Exception):
    """Base exception class for RAG pipeline."""
    pass

class ParsingException(RAGBaseException):
    """Raised when PDF parsing fails."""
    pass

class ChunkingException(RAGBaseException):
    """Raised when document chunking fails."""
    pass

class EmbeddingException(RAGBaseException):
    """Raised when embedding generation fails."""
    pass

class IndexingException(RAGBaseException):
    """Raised when FAISS indexing fails."""
    pass

class RetrievalException(RAGBaseException):
    """Raised when query retrieval or vector search fails."""
    pass
