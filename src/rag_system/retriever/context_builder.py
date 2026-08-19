"""
=============================================================================
  RETRIEVER FRAMEWORK — Context Builder
=============================================================================
  Assembles final Top-K retrieved chunks from ranked search candidates,
  performing deduplication, relevance/page sorting, metadata preservation,
  and token budget capping.
=============================================================================
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Set
from rag_system.config.settings import RetrieverConfig, DEFAULT_CONFIG
from rag_system.shared.models import RetrievedChunk

logger = logging.getLogger("ContextBuilder")


class ContextBuilder:
    """Assembles final Top-K context chunks while respecting token caps."""

    def __init__(self, cfg: RetrieverConfig = DEFAULT_CONFIG):
        self.cfg = cfg

    def build_context(
        self,
        candidates: List[Tuple[dict, float]],
        top_k: int | None = None,
        max_tokens: int | None = None,
        sort_by_page: bool | None = None
    ) -> List[RetrievedChunk]:
        """
        Deduplicates, caps, sorts, and converts candidate dictionaries into
        a final list of ranked RetrievedChunk domain objects.
        """
        k_final = top_k or self.cfg.top_k_final
        token_cap = max_tokens or self.cfg.max_context_tokens
        page_sort = sort_by_page if sort_by_page is not None else self.cfg.sort_by_page

        if not candidates:
            return []

        # 1. Deduplicate by chunk_id while preserving highest similarity score
        seen_ids: Set[str] = set()
        deduped: List[Tuple[dict, float]] = []

        for item, score in candidates:
            c_id = item.get("chunk_id", "")
            if c_id and c_id not in seen_ids:
                seen_ids.add(c_id)
                deduped.append((item, score))

        # 2. Limit to Top-K final
        selected_candidates = deduped[:k_final]

        # 3. Optional PDF Page-Order Sorting
        if page_sort:
            def get_page_start(x):
                item_dict = x[0]
                if "metadata" in item_dict and isinstance(item_dict["metadata"], dict):
                    return item_dict["metadata"].get("page_start", 1)
                return item_dict.get("page_start", 1)

            selected_candidates = sorted(
                selected_candidates,
                key=lambda x: (get_page_start(x), -x[1])
            )

        # 4. Token Budget Capping & Dataclass Construction
        retrieved_chunks = []
        current_tokens = 0

        for rank_idx, (item, score) in enumerate(selected_candidates, start=1):
            meta = item.get("metadata")
            if meta is None or not isinstance(meta, dict):
                # Build metadata dictionary from flat payload keys
                meta = {
                    "document_title": item.get("document_title", ""),
                    "chapter": item.get("chapter", ""),
                    "section": item.get("section", ""),
                    "subsection": item.get("subsection", ""),
                    "page_start": item.get("page_start", 1),
                    "page_end": item.get("page_end", 1),
                    "token_count": item.get("token_count", 0),
                    "language": item.get("language", "English"),
                    "layout_type": item.get("layout_type", "single_column"),
                    "semantic_class": item.get("semantic_class", ""),
                    "content_hash": item.get("content_hash", "")
                }

            t_count = meta.get("token_count", 0)

            if current_tokens + t_count > token_cap and len(retrieved_chunks) > 0:
                logger.debug(f"Context Builder token cap reached ({current_tokens} + {t_count} > {token_cap}). Stopping.")
                break

            chunk_obj = RetrievedChunk(
                chunk_id=item.get("chunk_id", ""),
                content=item.get("content", ""),
                score=score,
                rank=rank_idx,
                metadata=meta,
                table_references=item.get("table_references", []),
                figure_references=item.get("figure_references", [])
            )
            retrieved_chunks.append(chunk_obj)
            current_tokens += t_count

        return retrieved_chunks
