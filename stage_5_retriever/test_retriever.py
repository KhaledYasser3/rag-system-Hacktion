"""
=============================================================================
  STAGE 5: RETRIEVER FRAMEWORK — Test & Benchmark Suite
=============================================================================
  Runs clinical benchmark queries against MedicalRetriever and computes
  Recall@5, Recall@10, Precision@5, MRR, Hit Rate, nDCG, and Latency report.
=============================================================================
"""

from __future__ import annotations

import os
import sys

# Ensure parent directory is in Python path for clean imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stage_5_retriever.config import RetrieverConfig
from stage_5_retriever.models import BenchmarkQuery
from stage_5_retriever.retriever import MedicalRetriever
from stage_5_retriever.evaluator import RetrievalEvaluator


BENCHMARK_QUERIES = [
    BenchmarkQuery(
        query_id="BM_001",
        question="What is the recommended second-line treatment for type 2 diabetes when metformin fails?",
        relevant_chunk_ids=["chk_e3c85f0e_0019", "chk_e3c85f0e_0020", "chk_e3c85f0e_0021", "chk_e3c85f0e_0049"],
        category="Clinical Recommendation"
    ),
    BenchmarkQuery(
        query_id="BM_002",
        question="When should insulin be introduced in non-pregnant adults with diabetes mellitus?",
        relevant_chunk_ids=["chk_e3c85f0e_0029", "chk_e3c85f0e_0030", "chk_e3c85f0e_0031"],
        category="Treatment Protocol"
    ),
    BenchmarkQuery(
        query_id="BM_003",
        question="What are the critical outcomes evaluated for long-acting insulin analogues in Appendix 10?",
        relevant_chunk_ids=["chk_e3c85f0e_0083", "chk_e3c85f0e_0084", "chk_e3c85f0e_0085", "chk_e3c85f0e_0086"],
        category="Evidence Summary"
    ),
    BenchmarkQuery(
        query_id="BM_004",
        question="What are the PICO questions and ranked outcomes for blood glucose lowering medicines?",
        relevant_chunk_ids=["chk_e3c85f0e_0041", "chk_e3c85f0e_0042", "chk_e3c85f0e_0043"],
        category="Methodology & PICO"
    ),
    BenchmarkQuery(
        query_id="BM_005",
        question="What is the narrative review on cost-effectiveness of Type 1 and Type 2 diabetes medicines?",
        relevant_chunk_ids=["chk_e3c85f0e_0060", "chk_e3c85f0e_0061", "chk_e3c85f0e_0062"],
        category="Health Economics"
    )
]


def run_tests() -> None:
    """Executes retriever pipeline test suite and prints evaluation report."""
    print("=" * 72)
    print("  STAGE 5: MEDICAL RAG RETRIEVER EVALUATION SUITE")
    print("=" * 72)

    cfg = RetrieverConfig(
        top_k_initial=20,
        top_k_final=5,
        similarity_threshold=0.30,
        sort_by_page=False
    )

    print("[Test Engine] Initializing MedicalRetriever and FAISS Vector Store...")
    retriever = MedicalRetriever(cfg=cfg)

    evaluator = RetrievalEvaluator(retriever=retriever)

    print(f"[Test Engine] Running retrieval evaluation across {len(BENCHMARK_QUERIES)} benchmark queries...")
    metrics = evaluator.evaluate(BENCHMARK_QUERIES)

    evaluator.print_report(metrics)


if __name__ == "__main__":
    run_tests()
