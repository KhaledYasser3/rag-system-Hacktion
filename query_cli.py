"""
=============================================================================
  MEDICAL RAG AI ASSISTANT — INTERACTIVE CLI TESTER
=============================================================================
  Allows developers and clinical users to query Qdrant and verify the
  relevance and medical accuracy of the generated LLM responses.
  
  Run: python query_cli.py
  Run single query: python query_cli.py "your question here"
=============================================================================
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Configure python path to find src/ rag_system modules
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from rag_system.retriever.pipeline import MedicalRetriever
from rag_system.retriever.generator import MedicalGenerator


def run_query(retriever: MedicalRetriever, generator: MedicalGenerator, question: str) -> None:
    print("\n" + "=" * 75)
    print(f"❓ Question: {question}")
    print("=" * 75)

    # 1. Retrieve relevant contexts from Qdrant
    try:
        result = retriever.retrieve(question)
        chunks = result.chunks
        print(f"✅ Retrieved {len(chunks)} relevant context chunks:")
        
        for idx, chunk in enumerate(chunks, start=1):
            p_start = chunk.metadata.get("page_start", "?")
            p_end = chunk.metadata.get("page_end", p_start)
            page_ref = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}–{p_end}"
            chapter = chunk.metadata.get("chapter", "N/A")
            section = chunk.metadata.get("section", "N/A")
            
            print(f"\n   [Rank #{idx} | Score {chunk.score:.3f} | {page_ref}]")
            print(f"   Chapter: {chapter} > Section: {section}")
            print(f"   Content snippet: {chunk.content[:180].strip()}...")
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        return

    # 2. Generate answer via the clinical LLM generator
    print("\n🤖 Generating answer from clinical guidelines...")
    try:
        answer = generator.generate_answer(question, chunks)
        model_used = "Ollama" if generator.used_fallback else "Groq GPT-OSS-120B"
        print(f"\n--- ANSWER ({model_used}) ---")
        print(answer)
        print("-" * 75)
    except Exception as e:
        print(f"❌ Answer generation failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Interactive Medical RAG CLI Tester")
    parser.add_argument("query", nargs="?", type=str, help="Single question to query immediately")
    args = parser.parse_args()

    print("Initializing Medical Retriever...")
    retriever = MedicalRetriever()
    print("Initializing Medical Generator...")
    generator = MedicalGenerator(
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model="openai/gpt-oss-120b",
    )
    print("✨ RAG System ready for evaluation.\n")

    if args.query:
        run_query(retriever, generator, args.query.strip())
        return

    # Interactive mode loop
    print("=" * 75)
    print("  INTERACTIVE CLINICAL RAG TESTER")
    print("  Type 'exit' or 'quit' to close.")
    print("=" * 75)
    
    print("\n💡 Suggested test questions from the Guidelines:")
    print("   [English Questions]:")
    print("     - What is the recommended second-line treatment when metformin monotherapy fails?")
    print("     - When should insulin be initiated in type 2 diabetes management?")
    print("     - What is the difference between NPH insulin and insulin glargine?")
    print("     - What HbA1c threshold is used to define poor glycaemic control?")
    print("   [Arabic Questions]:")
    print("     - ما هو العلاج الموصى به عند فشل الميتفورمين؟")
    print("     - متى يجب البدء في استخدام الأنسولين لمرضى السكري من النوع الثاني؟")
    print("     - قارن بين أدوية السلفونيل يوريا ومثبطات DPP-4 لمرضى السكري.")

    while True:
        try:
            # Force utf-8 reading in terminal where possible
            query = input("\n[Question]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting assistant.")
            break

        if not query:
            continue

        if query.lower() in ("exit", "quit"):
            print("Exiting assistant.")
            break

        run_query(retriever, generator, query)


if __name__ == "__main__":
    main()
