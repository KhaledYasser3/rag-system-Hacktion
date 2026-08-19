"""
=============================================================================
  RAG SYSTEM — Manual Evaluation Script
=============================================================================
  Run: python test_query.py
  Run with custom question: python test_query.py "your question here"
  Run full suite: python test_query.py --all
=============================================================================
"""

import os
import sys
import time
import argparse
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from rag_system.retriever.pipeline import MedicalRetriever
from rag_system.retriever.generator import MedicalGenerator

# ─── Test Questions ───────────────────────────────────────────────────────────
# Covers different question types across the document
TEST_QUESTIONS = [
    # --- Direct / Definition ---
    ("DEF",  "What is type 2 diabetes mellitus?"),
    ("DEF",  "What does NPH insulin stand for?"),
    # --- Recommendation ---
    ("REC",  "What is the recommended second-line treatment when metformin monotherapy fails?"),
    ("REC",  "When should insulin be initiated in type 2 diabetes management?"),
    # --- Comparison ---
    ("CMP",  "What is the difference between NPH insulin and insulin glargine?"),
    ("CMP",  "Compare sulfonylureas and DPP-4 inhibitors for type 2 diabetes."),
    # --- Numerical / Threshold ---
    ("NUM",  "What HbA1c threshold is used to define poor glycaemic control?"),
    ("NUM",  "What is the recommended fasting blood glucose target?"),
    # --- Arabic ---
    ("ARB",  "ما هو العلاج الموصى به عند فشل الميتفورمين؟"),
    ("ARB",  "ما هي الأنسولينات الموصى بها لمرضى السكري من النوع الثاني؟"),
    # --- Unanswerable (should trigger refusal) ---
    ("N/A",  "What is the capital of France?"),
    ("N/A",  "Who wrote the book Pride and Prejudice?"),
]

SEP = "─" * 72


def run_single(retriever, generator, question: str, category: str = "?") -> None:
    print(f"\n{SEP}")
    print(f"  [{category}] {question}")
    print(SEP)

    t0 = time.time()
    try:
        result = retriever.retrieve(question=question, top_k=5, similarity_threshold=0.18)
        chunks = result.chunks
        elapsed_ret = (time.time() - t0) * 1000

        print(f"  ✅ Retrieved {len(chunks)} chunks  ({elapsed_ret:.0f} ms)")
        for i, c in enumerate(chunks, 1):
            pg = c.metadata.get("page_start", "?")
            sc = round(c.score, 3)
            print(f"     #{i} score={sc}  page={pg}  | {c.content[:90].strip()}...")

    except Exception as e:
        print(f"  ❌ Retrieval failed: {e}")
        return

    print()
    t1 = time.time()
    try:
        answer = generator.generate_answer(question, chunks)
        elapsed_gen = (time.time() - t1) * 1000
        model = "Ollama" if generator.used_fallback else "Groq GPT-OSS-120B"
        print(f"  🤖 [{model}] ({elapsed_gen:.0f} ms)")
        print(f"  {answer[:500]}{'...' if len(answer) > 500 else ''}")
    except Exception as e:
        print(f"  ❌ Generation failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="RAG System Test Runner")
    parser.add_argument("question", nargs="?", help="Single question to test")
    parser.add_argument("--all", action="store_true", help="Run full test suite")
    args = parser.parse_args()

    print(f"\n{'=' * 72}")
    print("  RAG SYSTEM — Evaluation Runner")
    print(f"{'=' * 72}\n")

    print("Initializing retriever...")
    retriever = MedicalRetriever()
    print("Initializing generator...")
    generator = MedicalGenerator(
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model="openai/gpt-oss-120b",
    )
    print("✅ Ready.\n")

    if args.question:
        # Run a single custom question
        run_single(retriever, generator, args.question, category="CUSTOM")
    elif args.all:
        # Run full suite
        print(f"Running {len(TEST_QUESTIONS)} test questions...\n")
        for category, question in TEST_QUESTIONS:
            run_single(retriever, generator, question, category)
    else:
        # Default: run first 3 as a quick smoke test
        print("Quick smoke test (3 questions). Use --all for full suite.\n")
        for category, question in TEST_QUESTIONS[:3]:
            run_single(retriever, generator, question, category)

    print(f"\n{'=' * 72}")
    print("  Done.")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    main()
