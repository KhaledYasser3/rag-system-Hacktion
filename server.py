"""
=============================================================================
  DOCUMENT RAG AI ASSISTANT — Flask API Backend
=============================================================================
  A Flask server that wraps the RAG pipeline and exposes it via API.
  Run: python server.py
  Then open: ui/index.html in your browser
=============================================================================
"""

import os
import sys
import re
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, request, jsonify
from flask_cors import CORS

from rag_system.retriever.pipeline import MedicalRetriever
from rag_system.retriever.generator import MedicalGenerator
from rag_system.retriever.prompt_builder import build_rag_prompt, detect_language

# ─── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("RAG_API")

# ─── Flask App ───────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow browser to call from any origin

# ─── Load pipeline once ──────────────────────────────────────────────────────
logger.info("Initializing RAG Retriever...")
try:
    retriever = MedicalRetriever(
        cohere_api_key=os.environ.get("COHERE_API_KEY", "")
    )
    logger.info("Retriever ready.")
except Exception as e:
    logger.error(f"Failed to initialize retriever: {e}")
    retriever = None


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    collection_count = 0
    if retriever:
        try:
            collection_count = retriever.vector_store.count()
        except Exception:
            pass
    return jsonify({
        "status": "ok" if retriever else "error",
        "indexed_chunks": collection_count,
        "qdrant": "connected" if retriever else "disconnected"
    })


@app.route("/api/query", methods=["POST"])
def query():
    """
    Main query endpoint.
    POST body: { "question": "...", "top_k": 5, "threshold": 0.30 }
    Returns:   { "answer": "...", "chunks": [...], "latency": {...}, "model_used": "...", "lang": "..." }
    """
    if not retriever:
        return jsonify({"error": "Retriever not initialized. Run python scripts/ingest.py first."}), 500

    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    top_k = int(data.get("top_k", 5))
    threshold = float(data.get("threshold", 0.30))

    if not question:
        return jsonify({"error": "question field is required"}), 400

    # ── Detect language BEFORE embedding ──────────────────────────────────────
    lang = detect_language(question)
    logger.info(f"Detected question language: {lang}")

    # For non-English (e.g. Arabic) questions the cosine similarity of the
    # Cohere cross-lingual space is generally lower → use a reduced threshold
    # so we still surface relevant English chunks to answer from.
    effective_threshold = threshold
    if lang == "arabic":
        effective_threshold = max(0.10, threshold - 0.15)
        logger.info(f"Arabic query: lowering similarity threshold {threshold} → {effective_threshold}")

    try:
        # 1. Retrieve from Qdrant
        search_result = retriever.retrieve(
            question=question,
            top_k=top_k,
            similarity_threshold=effective_threshold
        )
        chunks = search_result.chunks
        latency = search_result.latency_breakdown_ms
        logger.info(f"Retrieved {len(chunks)} chunks for question (lang={lang}).")

        # 2. Generate answer via LLM
        generator = MedicalGenerator(
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
            groq_model="openai/gpt-oss-120b",
            ollama_host="http://localhost:11434",
            ollama_model="llama3"
        )
        answer = generator.generate_answer(question, chunks)
        model_used = "Ollama (llama3 local)" if generator.used_fallback else "Groq (GPT-OSS-120B)"

        # 3. Serialize chunks for JSON response
        chunks_data = []
        for chunk in chunks:
            chunks_data.append({
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "score": round(chunk.score, 4),
                "page_start": chunk.metadata.get("page_start", "N/A"),
                "page_end": chunk.metadata.get("page_end", "N/A"),
                "chapter": chunk.metadata.get("chapter", ""),
                "section": chunk.metadata.get("section", ""),
            })

        return jsonify({
            "answer": answer,
            "chunks": chunks_data,
            "latency": latency,
            "model_used": model_used,
            "chunks_used": len(chunks),
            "total_candidates": search_result.total_initial_found,
            "lang": lang
        })

    except Exception as e:
        logger.error(f"Query failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  DOCUMENT RAG AI — Flask API Server")
    print("  API running at: http://localhost:5000")
    print("  Open ui/index.html in your browser")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
