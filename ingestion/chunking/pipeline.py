"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Pipeline Orchestrator
=============================================================================
  High-level flow:
  DocumentNode Tree
        ↓
  Normalized Structural Blocks
        ↓
  Content Classification
        ↓
  Strategy Selection & Execution
        ↓
  Context Enrichment (embedding_text construction)
        ↓
  Validation
        ↓
  Final StructureAwareChunk Objects
=============================================================================
"""

from __future__ import annotations

import os
import sys
import hashlib
import logging
from typing import List, Dict, Any, Optional

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.utils.token_utils import TokenCounter, get_token_counter
from ingestion.chunking.classifiers.content_classifier import ContentClassifier
from ingestion.chunking.strategies.base import StrategyRegistry
from ingestion.chunking.strategies.semantic import SemanticChunkingStrategy
from ingestion.chunking.strategies.glossary import GlossaryChunkingStrategy
from ingestion.chunking.strategies.table import TableChunkingStrategy
from ingestion.chunking.strategies.list_strategy import ListChunkingStrategy
from ingestion.chunking.strategies.figure import FigureChunkingStrategy
from ingestion.chunking.context.context_enricher import ContextEnricher
from ingestion.chunking.validators.chunk_validator import ChunkValidator

logger = logging.getLogger("ChunkingPipeline")


class ChunkingPipeline:
    """Production Pipeline Orchestrator for Structure-Aware Chunking."""

    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        token_counter: Optional[TokenCounter] = None,
        classifier: Optional[ContentClassifier] = None,
        strategy_registry: Optional[StrategyRegistry] = None,
        context_enricher: Optional[ContextEnricher] = None,
        validator: Optional[ChunkValidator] = None
    ):
        self.config = config or ChunkingConfig()
        self.token_counter = token_counter or get_token_counter(self.config.tokenizer_encoding)
        self.classifier = classifier or ContentClassifier()
        self.context_enricher = context_enricher or ContextEnricher(self.config)
        self.validator = validator or ChunkValidator(self.config)

        # Initialize Strategy Registry with default pluggable strategies
        if strategy_registry:
            self.registry = strategy_registry
        else:
            self.registry = StrategyRegistry([
                GlossaryChunkingStrategy(),
                TableChunkingStrategy(),
                FigureChunkingStrategy(),
                ListChunkingStrategy(),
                SemanticChunkingStrategy(), # Default prose fallback
            ])

        self._fig_counter = 1
        self._block_counter = 1

    def run(self, doc_tree: Any) -> List[StructureAwareChunk]:
        """
        Executes full structure-aware chunking pipeline on DocumentNode tree.
        """
        logger.info("Initializing Structure-Aware Chunking Pipeline...")
        self._fig_counter = 1
        self._block_counter = 1

        doc_title = getattr(doc_tree, "title", "Medical Guidelines")
        doc_prefix = hashlib.md5(doc_title.encode("utf-8")).hexdigest()[:8]

        # 1. Normalize tree nodes into StructuralBlocks
        blocks = self._normalize_blocks(doc_tree, doc_title)

        if not blocks:
            logger.warning("No structural blocks extracted from DocumentNode tree.")
            return []

        # 2. Strategy Execution Context
        context: Dict[str, Any] = {
            "doc_title": doc_title,
            "doc_prefix": doc_prefix,
            "chunk_counter": 1
        }

        raw_chunks: List[StructureAwareChunk] = []

        # 3. Strategy Selection & Chunk Generation per Block
        for block in blocks:
            strategy = self.registry.select_strategy(block)
            block_chunks = strategy.chunk(block, context, self.config, self.token_counter)
            raw_chunks.extend(block_chunks)

        # 4. Context Enrichment (generates embedding_text separate from content)
        enriched_chunks = []
        for chunk in raw_chunks:
            enriched = self.context_enricher.enrich(chunk)
            enriched_chunks.append(enriched)

        # 5. Validation
        is_valid, validation_issues = self.validator.validate(enriched_chunks)
        if is_valid:
            logger.info(f"Chunking completed successfully: {len(enriched_chunks)} chunks generated.")
        else:
            logger.warning(f"Chunking completed with {len(validation_issues)} validation notes.")

        return enriched_chunks

    def _normalize_blocks(self, node: Any, doc_title: str, ch: str = "", sec: str = "", sub: str = "") -> List[StructuralBlock]:
        """Depth-first traversal normalizing raw DocumentNode tree into StructuralBlocks."""
        blocks: List[StructuralBlock] = []
        node_type = getattr(node, "node_type", "")

        if node_type == "Document Title":
            for child in getattr(node, "children", []):
                blocks.extend(self._normalize_blocks(child, doc_title, ch, sec, sub))

        elif node_type in ("Chapter", "Appendix", "Document Title Heading"):
            ch_title = getattr(node, "title", ch)
            for child in getattr(node, "children", []):
                blocks.extend(self._normalize_blocks(child, doc_title, ch_title, "", sub))

        elif node_type == "Section":
            sec_title = getattr(node, "title", sec)
            for child in getattr(node, "children", []):
                blocks.extend(self._normalize_blocks(child, doc_title, ch, sec_title, ""))

        elif node_type == "Subsection":
            sub_title = getattr(node, "title", sub)
            for child in getattr(node, "children", []):
                blocks.extend(self._normalize_blocks(child, doc_title, ch, sec, sub_title))

        elif node_type in ("Paragraph", "Table", "Figure"):
            b_id = f"blk_{self._block_counter:04d}"
            self._block_counter += 1

            # Classify ContentType
            c_type = self.classifier.classify(node, ch, sec, sub)

            page_num = getattr(node, "page_number", 1)
            text = getattr(node, "text", "").strip()
            title = getattr(node, "title", getattr(node, "caption", ""))

            headers = getattr(node, "headers", [])
            rows = getattr(node, "rows", [])

            metadata = {}
            if node_type == "Figure":
                fig_id = f"fig_{self._fig_counter:03d}"
                self._fig_counter += 1
                fig_cap = getattr(node, "caption", f"Figure Page {page_num}")
                img_p = getattr(node, "image_path", "media/figure.png")
                metadata["figure_meta"] = {
                    "figure_id": fig_id,
                    "caption": fig_cap,
                    "page": page_num,
                    "image_path": img_p
                }

            s_block = StructuralBlock(
                block_id=b_id,
                content_type=c_type,
                text=text,
                page_number=page_num,
                chapter=ch or doc_title,
                section=sec,
                subsection=sub,
                title=title,
                headers=headers,
                rows=rows,
                metadata=metadata,
                raw_node=node
            )
            blocks.append(s_block)

        return blocks


if __name__ == "__main__":
    from ingestion.chunker import run_chunking_evaluation
    from ingestion.parser import advanced_parse_pdf
    from ingestion.hierarchy_builder import HierarchyBuilder

    PDF_PATH = os.path.join("data", "pdfs", "9789241550284-eng.pdf")
    print(f"[Chunking Pipeline CLI] Parsing PDF: {PDF_PATH} ...")
    parsed_docs, _ = advanced_parse_pdf(PDF_PATH)

    builder = HierarchyBuilder()
    doc_tree = builder.build(parsed_docs)

    run_chunking_evaluation(doc_tree)
