"""
=============================================================================
  SHARED DATA MODELS
=============================================================================
  Dataclass definitions representing queries, search candidates, final
  retrieved chunks, search results, benchmark queries, and evaluation metrics.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Query:
    """Preprocessed query representation."""
    raw_query: str
    processed_query: str
    normalized_query: str
    expanded_terms: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None


@dataclass
class RetrievedChunk:
    """A ranked chunk candidate retrieved for a query."""
    chunk_id: str
    content: str
    score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    table_references: List[str] = field(default_factory=list)
    figure_references: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def page_start(self) -> int:
        return self.metadata.get("page_start", 1)

    @property
    def page_end(self) -> int:
        return self.metadata.get("page_end", 1)

    @property
    def token_count(self) -> int:
        return self.metadata.get("token_count", 0)

    @property
    def chapter(self) -> str:
        return self.metadata.get("chapter", "")

    @property
    def section(self) -> str:
        return self.metadata.get("section", "")

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": round(self.score, 4),
            "rank": self.rank,
            "metadata": self.metadata,
            "table_references": self.table_references,
            "figure_references": self.figure_references
        }


@dataclass
class SearchResult:
    """Aggregated output of the complete retrieval pipeline."""
    query: Query
    chunks: List[RetrievedChunk]
    total_initial_found: int
    latency_breakdown_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": self.query.raw_query,
            "total_initial_found": self.total_initial_found,
            "retrieved_count": len(self.chunks),
            "latency_breakdown_ms": self.latency_breakdown_ms,
            "chunks": [c.to_dict() for c in self.chunks]
        }


@dataclass
class BenchmarkQuery:
    """Ground-truth benchmark query item for evaluation."""
    query_id: str
    question: str
    relevant_chunk_ids: List[str]
    category: str = "Clinical Recommendation"


@dataclass
class EvaluationMetrics:
    """Aggregated metrics evaluation summary across query benchmark sets."""
    queries_tested: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float
    precision_at_1: float
    precision_at_3: float
    precision_at_5: float
    precision_at_10: float
    f1_at_5: float
    f1_at_10: float
    mrr: float
    hit_rate: float
    ndcg_at_3: float
    ndcg_at_5: float
    ndcg_at_10: float
    map: float
    avg_similarity_score: float
    avg_embedding_latency_ms: float
    avg_search_latency_ms: float
    avg_rerank_latency_ms: float
    avg_total_latency_ms: float
    throughput_qps: float
