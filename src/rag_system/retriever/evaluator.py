"""
=============================================================================
  RETRIEVER FRAMEWORK — Evaluation Framework
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
from rag_system.shared.models import BenchmarkQuery, EvaluationMetrics, SearchResult
from rag_system.retriever.pipeline import MedicalRetriever
from rag_system.retriever.metrics import (
    calculate_recall_at_k,
    calculate_precision_at_k,
    calculate_mrr,
    calculate_hit_rate,
    calculate_ndcg_at_k,
    calculate_ap,
    calculate_f1_score
)
from rag_system.shared.utils import safe_print

logger = logging.getLogger("RetrievalEvaluator")


class RetrievalEvaluator:
    """Evaluates MedicalRetriever performance against ground-truth benchmarks."""

    def __init__(self, retriever: MedicalRetriever):
        self.retriever = retriever

    def evaluate(self, benchmarks: List[BenchmarkQuery]) -> EvaluationMetrics:
        """Executes benchmarks and computes aggregated evaluation metrics."""
        if not benchmarks:
            raise ValueError("Benchmark query list cannot be empty.")

        recalls_1 = []
        recalls_3 = []
        recalls_5 = []
        recalls_10 = []
        precisions_1 = []
        precisions_3 = []
        precisions_5 = []
        precisions_10 = []
        f1s_5 = []
        f1s_10 = []
        mrrs = []
        hit_rates = []
        ndcgs_3 = []
        ndcgs_5 = []
        ndcgs_10 = []
        aps = []
        similarity_scores = []

        processing_latencies = []
        embedding_latencies = []
        search_latencies = []
        rerank_latencies = []
        total_latencies = []

        t_eval_start = time.time()

        for b_query in benchmarks:
            res: SearchResult = self.retriever.retrieve(b_query.question, top_k=10)

            retrieved_ids = [c.chunk_id for c in res.chunks]
            truth_ids = b_query.relevant_chunk_ids

            rec_1 = calculate_recall_at_k(retrieved_ids, truth_ids, k=1)
            rec_3 = calculate_recall_at_k(retrieved_ids, truth_ids, k=3)
            rec_5 = calculate_recall_at_k(retrieved_ids, truth_ids, k=5)
            rec_10 = calculate_recall_at_k(retrieved_ids, truth_ids, k=10)

            prec_1 = calculate_precision_at_k(retrieved_ids, truth_ids, k=1)
            prec_3 = calculate_precision_at_k(retrieved_ids, truth_ids, k=3)
            prec_5 = calculate_precision_at_k(retrieved_ids, truth_ids, k=5)
            prec_10 = calculate_precision_at_k(retrieved_ids, truth_ids, k=10)

            recalls_1.append(rec_1)
            recalls_3.append(rec_3)
            recalls_5.append(rec_5)
            recalls_10.append(rec_10)

            precisions_1.append(prec_1)
            precisions_3.append(prec_3)
            precisions_5.append(prec_5)
            precisions_10.append(prec_10)

            f1s_5.append(calculate_f1_score(prec_5, rec_5))
            f1s_10.append(calculate_f1_score(prec_10, rec_10))

            mrrs.append(calculate_mrr(retrieved_ids, truth_ids))
            hit_rates.append(calculate_hit_rate(retrieved_ids, truth_ids))
            
            ndcgs_3.append(calculate_ndcg_at_k(retrieved_ids, truth_ids, k=3))
            ndcgs_5.append(calculate_ndcg_at_k(retrieved_ids, truth_ids, k=5))
            ndcgs_10.append(calculate_ndcg_at_k(retrieved_ids, truth_ids, k=10))

            aps.append(calculate_ap(retrieved_ids, truth_ids))

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
            recall_at_1=sum(recalls_1) / total_q,
            recall_at_3=sum(recalls_3) / total_q,
            recall_at_5=sum(recalls_5) / total_q,
            recall_at_10=sum(recalls_10) / total_q,
            precision_at_1=sum(precisions_1) / total_q,
            precision_at_3=sum(precisions_3) / total_q,
            precision_at_5=sum(precisions_5) / total_q,
            precision_at_10=sum(precisions_10) / total_q,
            f1_at_5=sum(f1s_5) / total_q,
            f1_at_10=sum(f1s_10) / total_q,
            mrr=sum(mrrs) / total_q,
            hit_rate=sum(hit_rates) / total_q,
            ndcg_at_3=sum(ndcgs_3) / total_q,
            ndcg_at_5=sum(ndcgs_5) / total_q,
            ndcg_at_10=sum(ndcgs_10) / total_q,
            map=sum(aps) / total_q,
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
        safe_print("\n" + "=" * 60)
        safe_print(" RETRIEVAL EVALUATION REPORT")
        safe_print("=" * 60)
        safe_print(f" Queries Tested : {metrics.queries_tested}")
        safe_print("-" * 60)
        safe_print(" RETRIEVAL ACCURACY METRICS")
        safe_print(f" ✓ Recall@1 : {metrics.recall_at_1:.4f}")
        safe_print(f" ✓ Recall@3 : {metrics.recall_at_3:.4f}")
        safe_print(f" ✓ Recall@5 : {metrics.recall_at_5:.4f}")
        safe_print(f" ✓ Recall@10 : {metrics.recall_at_10:.4f}")
        safe_print(f" ✓ Precision@1 : {metrics.precision_at_1:.4f}")
        safe_print(f" ✓ Precision@3 : {metrics.precision_at_3:.4f}")
        safe_print(f" ✓ Precision@5 : {metrics.precision_at_5:.4f}")
        safe_print(f" ✓ Precision@10 : {metrics.precision_at_10:.4f}")
        safe_print(f" ✓ F1-Score@5 : {metrics.f1_at_5:.4f}")
        safe_print(f" ✓ F1-Score@10 : {metrics.f1_at_10:.4f}")
        safe_print(f" ✓ MRR (Mean Reciprocal Rank): {metrics.mrr:.4f}")
        safe_print(f" ✓ Hit Rate : {metrics.hit_rate:.4f}")
        safe_print(f" ✓ nDCG@3 : {metrics.ndcg_at_3:.4f}")
        safe_print(f" ✓ nDCG@5 : {metrics.ndcg_at_5:.4f}")
        safe_print(f" ✓ nDCG@10 : {metrics.ndcg_at_10:.4f}")
        safe_print(f" ✓ MAP (Mean Average Precision): {metrics.map:.4f}")
        safe_print(f" ✓ Average Similarity : {metrics.avg_similarity_score:.4f}")
        safe_print("-" * 60)
        safe_print(" LATENCY & THROUGHPUT BREAKDOWN")
        safe_print(f" ✓ Average Embedding Time : {metrics.avg_embedding_latency_ms:.2f} ms")
        safe_print(f" ✓ Average Search Time : {metrics.avg_search_latency_ms:.2f} ms")
        safe_print(f" ✓ Average Ranking Time : {metrics.avg_rerank_latency_ms:.2f} ms")
        safe_print(f" ✓ Average Total Latency : {metrics.avg_total_latency_ms:.2f} ms")
        safe_print(f" ✓ Throughput (QPS) : {metrics.throughput_qps:.2f} queries/sec")
        safe_print("=" * 60 + "\n")
