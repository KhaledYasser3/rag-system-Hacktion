"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Strategy Base & Registry
=============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ingestion.chunking.models import StructuralBlock, StructureAwareChunk
from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.utils.token_utils import TokenCounter


class ChunkingStrategy(ABC):
    """Abstract interface for all chunking strategies."""

    @abstractmethod
    def can_handle(self, block: StructuralBlock) -> bool:
        """Return True if this strategy can process the structural block."""
        pass

    @abstractmethod
    def chunk(
        self,
        block: StructuralBlock,
        context: Dict[str, Any],
        config: ChunkingConfig,
        token_counter: TokenCounter
    ) -> List[StructureAwareChunk]:
        """Chunks a structural block into one or more StructureAwareChunk objects."""
        pass


class StrategyRegistry:
    """Registry that selects the appropriate strategy for a given block."""

    def __init__(self, strategies: Optional[List[ChunkingStrategy]] = None):
        self._strategies: List[ChunkingStrategy] = strategies or []

    def register(self, strategy: ChunkingStrategy) -> None:
        """Registers a new chunking strategy."""
        self._strategies.append(strategy)

    def select_strategy(self, block: StructuralBlock) -> ChunkingStrategy:
        """Selects the first strategy that can handle the structural block."""
        for strategy in self._strategies:
            if strategy.can_handle(block):
                return strategy
        raise ValueError(f"No strategy found to handle block type '{block.content_type}'.")
