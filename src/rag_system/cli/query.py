"""
=============================================================================
  MEDICAL RAG AI ASSISTANT — MAIN CLI ENTRY POINT
=============================================================================
  Interactive CLI dashboard for doctors to query WHO Guidelines and receive
  diagnoses, recommendations, and explicit page citations.
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rag_system.retriever.pipeline import MedicalRetriever

def main():
    print("=" * 70)
    print("  MEDICAL RAG AI ASSISTANT — WHO GUIDELINES CONSULTANT")
    print("  Type 'exit' to quit")
    print("=" * 70)

    try:
        retriever = MedicalRetriever()
    except Exception as e:
        print(f"\n[Initialization Notice] {e}")
        print("Note: To build or update the vector index, run the ingestion pipeline:")
        print("    python -m ingestion.pipeline\n")
        return

    while True:
        try:
            question = input("\n[Doctor Query]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting assistant.")
            break

        if question.lower() in ("exit", "quit"):
            print("Exiting assistant.")
            break

        if not question:
            continue

        result = retriever.retrieve(question)

        print("\n" + "=" * 70)
        print(f"Question: {question}")
        print("=" * 70)

        print(f"Retrieved {len(result.chunks)} relevant guideline chunks:")
        print()

        for i, chunk in enumerate(result.chunks, 1):
            print("-" * 70)
            print(f"Rank     : {i}")
            print(f"Score    : {chunk.score:.4f}")
            print(f"Chunk ID : {chunk.chunk_id}")
            print(f"Page     : {chunk.metadata.get('page_start')}")
            print(f"Chapter  : {chunk.metadata.get('chapter')}")
            print(f"Section  : {chunk.metadata.get('section')}")
            print()
            print(chunk.content[:700])
            print()

        print("=" * 70)
        print("Latency Breakdown:")
        for k, v in result.latency_breakdown_ms.items():
            print(f"  {k:20} : {v:.2f} ms")


if __name__ == "__main__":
    main()
