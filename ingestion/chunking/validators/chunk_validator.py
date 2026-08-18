"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Chunk Validator
=============================================================================
  Strict validation engine for generated chunks, verifying schema integrity,
  non-empty content, valid token counts, table header presence, and glossary
  term completeness.
=============================================================================
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any, Optional
from ingestion.chunking.models import StructureAwareChunk, ContentType
from ingestion.chunking.config import ChunkingConfig

logger = logging.getLogger("ChunkValidator")


class ChunkValidator:
    """Validates list of generated chunks against quality and structure rules."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()

    def validate(self, chunks: List[StructureAwareChunk]) -> Tuple[bool, List[str]]:
        """
        Executes validation suite across generated chunks.
        Returns (is_valid_bool, list_of_warning_or_error_messages).
        """
        issues: List[str] = []
        seen_ids = set()

        if not chunks:
            issues.append("❌ CRITICAL: Chunk list is completely empty.")
            return False, issues

        for idx, chunk in enumerate(chunks, start=1):
            c_prefix = f"Chunk [{idx} | ID: {chunk.chunk_id or 'MISSING'}]"

            # 1. Check Chunk ID
            if not chunk.chunk_id:
                issues.append(f"{c_prefix}: Missing chunk_id.")
            elif chunk.chunk_id in seen_ids:
                issues.append(f"{c_prefix}: Duplicate chunk_id '{chunk.chunk_id}'.")
            else:
                seen_ids.add(chunk.chunk_id)

            # 2. Check Content
            if not chunk.content or not chunk.content.strip():
                issues.append(f"{c_prefix}: Content is empty or contains only whitespace.")

            # 3. Check Embedding Text
            if not chunk.embedding_text or not chunk.embedding_text.strip():
                issues.append(f"{c_prefix}: embedding_text is empty.")

            # 4. Check Token Count
            if chunk.token_count <= 0:
                issues.append(f"{c_prefix}: Token count is zero or negative ({chunk.token_count}).")

            # 5. Check Content-Type Specific Integrity
            if chunk.content_type == ContentType.GLOSSARY_ENTRY:
                if not chunk.title or chunk.title.startswith("Table Page"):
                    issues.append(f"{c_prefix}: Glossary entry is missing a specific term name.")

            elif chunk.content_type == ContentType.TABLE:
                if "---" not in chunk.content and "Column 1" in chunk.content:
                    issues.append(f"{c_prefix}: Table chunk may contain orphan rows without valid headers.")

            # 6. Check Page Range
            if chunk.page_start <= 0 or chunk.page_end < chunk.page_start:
                issues.append(f"{c_prefix}: Invalid page range [{chunk.page_start}-{chunk.page_end}].")

        is_valid = len(issues) == 0
        if not is_valid:
            for issue in issues:
                logger.warning(issue)

            if self.config.strict_validation:
                critical_issues = [i for i in issues if "CRITICAL" in i or "empty" in i]
                if critical_issues:
                    raise ValueError(f"Chunk Validation Failed with {len(critical_issues)} critical issues: {critical_issues[0]}")

        return is_valid, issues
