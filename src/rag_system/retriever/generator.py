"""
=============================================================================
  RETRIEVER FRAMEWORK — High-Availability Medical Generator
=============================================================================
  Integrates Groq API and local Ollama failover generation.
  Automatically falls back to local Ollama if the cloud API fails.
=============================================================================
"""

from __future__ import annotations

import os
import sys
import logging
from typing import List, Optional
from rag_system.shared.models import RetrievedChunk
from rag_system.llm import GroqGenerator, OllamaGenerator, FailoverGenerator

logger = logging.getLogger("MedicalGenerator")


class MedicalGenerator:
    """High-Availability Generator trying Groq Llama 70B first, falling back to Ollama."""

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_model: str = "openai/gpt-oss-120b",
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llama3"
    ):
        # 1. Initialize Groq API Generator (Cloud)
        api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "").strip()
        self.primary = GroqGenerator(api_key=api_key, model=groq_model)
        
        # 2. Initialize Ollama Generator (Local Fallback)
        self.fallback = OllamaGenerator(host=ollama_host, model=ollama_model)
        
        # 3. Create the Failover wrapper
        self.failover_engine = FailoverGenerator(primary=self.primary, fallback=self.fallback)

    @property
    def used_fallback(self) -> bool:
        """Returns True if the last generation operation fell back to the local model."""
        return self.failover_engine.last_used_fallback

    def generate_answer(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        model_choice: str = "Cloud API (Groq)"
    ) -> str:
        """
        Generates clinical recommendations using the selected model choice:
        - "Cloud API (Groq)": Runs the Groq cloud engine (with failover to Ollama).
        - "Qwen 3B (Colab Server)": Directly routes to Qwen 3B running on Colab via Cloudflare Tunnel.
        """
        if model_choice == "Qwen 3B (Colab Server)":
            colab_url = os.environ.get("COLAB_TUNNEL_URL", "").strip()
            if not colab_url or "your-tunnel-link" in colab_url:
                return "[Configuration Error]: COLAB_TUNNEL_URL is not set or invalid in your .env file. Please paste your Cloudflare Tunnel URL there."
            
            logger.info(f"Routing query directly to custom Qwen 3B on Colab server: {colab_url}")
            try:
                import json
                import urllib.request
                from rag_system.retriever.prompt_builder import build_rag_prompt
                
                prompt = build_rag_prompt(query, chunks)
                url = f"{colab_url.rstrip('/')}/v1/chat/completions"
                payload = json.dumps({
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 512,
                    "temperature": 0.2
                }).encode("utf-8")
                
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    if "choices" in res_data:
                        return res_data["choices"][0]["message"]["content"].strip()
                    elif "error" in res_data:
                        return f"[Colab Server Error]: {res_data['error']}"
                    return str(res_data)
            except Exception as e:
                return f"[Generation Error - Colab Server is unreachable]: {e}"

        # Default behaviour: Cloud API (Groq)
        if not self.primary.api_key:
            logger.warning("No Groq API Key found. Directly routing to local fallback generator (Ollama).")
            try:
                res = self.fallback.generate_answer(query, chunks)
                self.failover_engine.last_used_fallback = True
                return res
            except Exception as e:
                return f"[Generation Error - Both API Key missing and Ollama offline]: {e}"
        
        # Run failover generation engine (Primary Groq -> Fallback Ollama)
        return self.failover_engine.generate_answer(query, chunks)
