"""
JSON Schema definitions for chunks, metadata, and embeddings.
"""

CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "chunk_id": {"type": "string"},
        "document_title": {"type": "string"},
        "chapter": {"type": "string"},
        "section": {"type": "string"},
        "subsection": {"type": "string"},
        "page_start": {"type": "integer"},
        "page_end": {"type": "integer"},
        "token_count": {"type": "integer"},
        "content": {"type": "string"},
        "table_references": {"type": "array"},
        "figure_references": {"type": "array"},
    },
    "required": ["chunk_id", "content"],
}
