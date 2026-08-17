"""
=============================================================================
  STAGE 5: RETRIEVER FRAMEWORK — Evaluation Framework
=============================================================================
  Evaluates retrieval performance across benchmark query sets, calculating
  Recall, Precision, MRR, Hit Rate, nDCG, latencies, and QPS throughput.
=============================================================================
"""

from __future__ import annotations

import time
import sys
import logging
from typing import List
from stage_5_retriever.models import BenchmarkQuery, EvaluationMetrics, SearchResult
from stage_5_retriever.retriever import MedicalRetriever
from stage_5_retriever.metrics import (
    calculate_recall_at_k,
    calculate_precision_at_k,
    calculate_mrr,
    calculate_hit_rate,
    calculate_ndcg_at_k
)

logger = logging.getLogger("RetrievalEvaluator")


def _safe_print(*args, **kwargs) -> None:
    """Print with ASCII fallback — always flushes to avoid output ordering bugs."""
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    msg = sep.join(str(a) for a in args) + end
    # Replace unicode symbols with ASCII equivalents
    msg = (msg
           .replace("✅", "[OK]")
           .replace("⚠️", "[WARN]")
           .replace("❌", "[FAIL]")
           .replace("✓", "[PASS]"))
    try:
        sys.stdout.write(msg)
        sys.stdout.flush()
    except UnicodeEncodeError:
        sys.stdout.buffer.write(msg.encode("ascii", errors="replace"))
        sys.stdout.flush()


class RetrievalEvaluator:
    """Evaluates MedicalRetriever performance against ground-truth benchmarks."""

    def __init__(self, retriever: MedicalRetriever):
        self.retriever = retriever

    def evaluate(self, benchmarks: List[BenchmarkQuery]) -> EvaluationMetrics:
        """Executes benchmarks and computes aggregated evaluation metrics."""
        if not benchmarks:
            raise ValueError("Benchmark query list cannot be empty.")

        recalls_5 = []
        recalls_10 = []
        precisions_5 = []
        mrrs = []
        hit_rates = []
        ndcgs_5 = []
        similarity_scores = []

        processing_latencies = []
        embedding_latencies = []
        search_latencies = []
        rerank_latencies = []
        total_latencies = []

        t_eval_start = time.time()

        for b_query in benchmarks:
            # Run top-10 retrieval for evaluation
            res: SearchResult = self.retriever.retrieve(b_query.question, top_k=10)

            retrieved_ids = [c.chunk_id for c in res.chunks]
            truth_ids = b_query.relevant_chunk_ids

            recalls_5.append(calculate_recall_at_k(retrieved_ids, truth_ids, k=5))
            recalls_10.append(calculate_recall_at_k(retrieved_ids, truth_ids, k=10))
            precisions_5.append(calculate_precision_at_k(retrieved_ids, truth_ids, k=5))
            mrrs.append(calculate_mrr(retrieved_ids, truth_ids))
            hit_rates.append(calculate_hit_rate(retrieved_ids, truth_ids))
            ndcgs_5.append(calculate_ndcg_at_k(retrieved_ids, truth_ids, k=5))

            if res.chunks:
                avg_sim = sum(c.score for c in res.chunks) / len(res.chunks)
                similarity_scores.append(avg_sim)

            lat = res.latency_breakdown_ms
            embedding_latencies.append(lat.get("embedding_ms", 0.0))
            search_latencies.append(lat.get("search_ms", 0.0))
            rerank_latencies.append(lat.get("rerank_ms", 0.0))
            total_latencies.append(lat.get("total_ms", 0.0))

        eval_duration = time.time() - t_eval_start
        total_q = len(benchmarks)

        metrics = EvaluationMetrics(
            queries_tested=total_q,
            recall_at_5=sum(recalls_5) / total_q,
            recall_at_10=sum(recalls_10) / total_q,
            precision_at_5=sum(precisions_5) / total_q,
            mrr=sum(mrrs) / total_q,
            hit_rate=sum(hit_rates) / total_q,
            ndcg_at_5=sum(ndcgs_5) / total_q,
            avg_similarity_score=(sum(similarity_scores) / len(similarity_scores)) if similarity_scores else 0.0,
            avg_embedding_latency_ms=sum(embedding_latencies) / total_q,
            avg_search_latency_ms=sum(search_latencies) / total_q,
            avg_rerank_latency_ms=sum(rerank_latencies) / total_q,
            avg_total_latency_ms=sum(total_latencies) / total_q,
            throughput_qps=(total_q / eval_duration) if eval_duration > 0 else 0.0
        )

        return metrics

    def print_report(self, metrics: EvaluationMetrics) -> None:
        """Prints beautifully formatted retrieval evaluation report."""
        _safe_print("\n" + "=" * 60)
        _safe_print(" RETRIEVAL EVALUATION REPORT")
        _safe_print("=" * 60)
        _safe_print(f"  Queries Tested           : {metrics.queries_tested}")
        _safe_print("-" * 60)
        _safe_print("  RETRIEVAL ACCURACY METRICS")
        _safe_print(f"  ✓ Recall@5               : {metrics.recall_at_5:.4f}")
        _safe_print(f"  ✓ Recall@10              : {metrics.recall_at_10:.4f}")
        _safe_print(f"  ✓ Precision@5            : {metrics.precision_at_5:.4f}")
        _safe_print(f"  ✓ MRR (Mean Reciprocal Rank): {metrics.mrr:.4f}")
        _safe_print(f"  ✓ Hit Rate               : {metrics.hit_rate:.4f}")
        _safe_print(f"  ✓ nDCG@5                 : {metrics.ndcg_at_5:.4f}")
        _safe_print(f"  ✓ Average Similarity     : {metrics.avg_similarity_score:.4f}")
        _safe_print("-" * 60)
        _safe_print("  LATENCY & THROUGHPUT BREAKDOWN")
        _safe_print(f"  ✓ Average Embedding Time : {metrics.avg_embedding_latency_ms:.2f} ms")
        _safe_print(f"  ✓ Average Search Time    : {metrics.avg_search_latency_ms:.2f} ms")
        _safe_print(f"  ✓ Average Ranking Time   : {metrics.avg_rerank_latency_ms:.2f} ms")
        _safe_print(f"  ✓ Average Total Latency  : {metrics.avg_total_latency_ms:.2f} ms")
        _safe_print(f"  ✓ Throughput (QPS)       : {metrics.throughput_qps:.2f} queries/sec")
        _safe_print("=" * 60 + "\n")
