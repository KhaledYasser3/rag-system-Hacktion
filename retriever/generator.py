"""
=============================================================================
  RETRIEVER FRAMEWORK — Generator Module
=============================================================================
  Integrates LLM generation (Ollama, Gemini, OpenAI) to generate clinical
  responses grounded in retrieved context with explicit page citations.
=============================================================================
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import List, Optional
from shared.models import RetrievedChunk
from retriever.prompt_builder import build_rag_prompt


class MedicalGenerator:
    """Generates clinical answers using Ollama or external LLM API."""

    def __init__(self, model_name: str = "gemini-flash", ollama_host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_host = ollama_host.rstrip("/")

    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        """
        Builds RAG prompt and queries LLM to produce cited medical recommendation.
        """
        prompt = build_rag_prompt(query, chunks)
        
        # Default local Ollama generation call fallback
        url = f"{self.ollama_host}/api/generate"
        payload = json.dumps({
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except Exception as e:
            # Return formatted structured context response if LLM server is not running
            return f"[Context Prepared - LLM Connection Pending]\n\n{prompt}"
