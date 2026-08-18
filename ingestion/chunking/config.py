"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Configuration
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ChunkingConfig:
    """Centralized configuration for Structure-Aware Chunking Pipeline."""
    target_chunk_tokens: int = 400
    max_chunk_tokens: int = 500
    min_chunk_tokens: int = 50
    overlap_tokens: int = 60

    # Tokenizer settings
    tokenizer_encoding: str = "cl100k_base"

    # Glossary Strategy settings
    glossary_atomic_entries: bool = True
    split_long_glossary_definitions: bool = True

    # Table Strategy settings
    preserve_table_headers: bool = True
    max_table_chunk_tokens: int = 450

    # Context Enrichment settings
    include_hierarchy_in_embedding_text: bool = True
    include_continuation_markers: bool = True

    # Validation settings
    strict_validation: bool = True
    allow_empty_chunks: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_chunk_tokens": self.target_chunk_tokens,
            "max_chunk_tokens": self.max_chunk_tokens,
            "min_chunk_tokens": self.min_chunk_tokens,
            "overlap_tokens": self.overlap_tokens,
            "tokenizer_encoding": self.tokenizer_encoding,
            "glossary_atomic_entries": self.glossary_atomic_entries,
            "preserve_table_headers": self.preserve_table_headers,
            "strict_validation": self.strict_validation,
        }
