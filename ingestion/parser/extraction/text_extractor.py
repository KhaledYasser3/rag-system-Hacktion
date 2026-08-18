"""
=============================================================================
  MODULAR PDF PARSER — Text Line & Word Extractor
=============================================================================
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple
from ingestion.parser.models import ContentBlock, BlockType

logger = logging.getLogger("TextExtractor")


class TextExtractor:
    """Extracts raw text words, font attributes, and character bounding boxes."""

    def extract_words(self, page_obj: Any) -> List[Dict[str, Any]]:
        """Extracts words with character attributes (size, fontname, x0, top, x1, bottom)."""
        try:
            return page_obj.extract_words(keep_blank_chars=False)
        except Exception as e:
            logger.error(f"Failed to extract words from page: {e}")
            return []
