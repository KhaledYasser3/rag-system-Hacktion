"""
=============================================================================
  RETRIEVER FRAMEWORK — Metrics Calculations
=============================================================================
  Pure mathematical metric calculations for Information Retrieval (IR)
  evaluations: Recall@K, Precision@K, MRR, Hit Rate, nDCG@K.
=============================================================================
"""

from __future__ import annotations

import math
from typing import List, Set


def calculate_recall_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
    """Calculates Recall@K: proportion of relevant ground truth chunks retrieved in Top-K."""
    if not ground_truth_ids:
        return 0.0
    k_retrieved = set(retrieved_ids[:k])
    truth_set = set(ground_truth_ids)
    hits = len(k_retrieved.intersection(truth_set))
    return hits / len(truth_set)


def calculate_precision_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
    """Calculates Precision@K: proportion of Top-K retrieved chunks that are relevant."""
    if k <= 0:
        return 0.0
    k_retrieved = retrieved_ids[:k]
    truth_set = set(ground_truth_ids)
    hits = sum(1 for cid in k_retrieved if cid in truth_set)
    return hits / float(k)


def calculate_mrr(retrieved_ids: List[str], ground_truth_ids: List[str]) -> float:
    """Calculates Mean Reciprocal Rank (MRR): 1 / rank of first relevant retrieved chunk."""
    truth_set = set(ground_truth_ids)
    for rank_idx, cid in enumerate(retrieved_ids, start=1):
        if cid in truth_set:
            return 1.0 / float(rank_idx)
    return 0.0


def calculate_hit_rate(retrieved_ids: List[str], ground_truth_ids: List[str]) -> float:
    """Calculates Hit Rate: 1.0 if at least one relevant ground truth chunk is retrieved, else 0.0."""
    truth_set = set(ground_truth_ids)
    for cid in retrieved_ids:
        if cid in truth_set:
            return 1.0
    return 0.0


def calculate_ndcg_at_k(retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
    """Calculates Normalized Discounted Cumulative Gain (nDCG@K)."""
    if not ground_truth_ids or k <= 0:
        return 0.0

    truth_set = set(ground_truth_ids)

    dcg = 0.0
    for i, cid in enumerate(retrieved_ids[:k], start=1):
        if cid in truth_set:
            dcg += 1.0 / math.log2(i + 1)

    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(truth_set), k) + 1))

    return (dcg / idcg) if idcg > 0 else 0.0


def calculate_ap(retrieved_ids: List[str], ground_truth_ids: List[str]) -> float:
    """Calculates Average Precision (AP) for a single query."""
    if not ground_truth_ids or not retrieved_ids:
        return 0.0
    truth_set = set(ground_truth_ids)
    hits = 0
    sum_precisions = 0.0
    for rank_idx, cid in enumerate(retrieved_ids, start=1):
        if cid in truth_set:
            hits += 1
            sum_precisions += hits / float(rank_idx)
    return sum_precisions / len(truth_set)


def calculate_f1_score(precision: float, recall: float) -> float:
    """Calculates F1-Score from Precision and Recall."""
    if (precision + recall) == 0.0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)

