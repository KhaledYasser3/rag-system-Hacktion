"""
Base abstractions re-export.
"""
from ingestion.chunking.strategies.base import ChunkingStrategy, StrategyRegistry

__all__ = ["ChunkingStrategy", "StrategyRegistry"]
