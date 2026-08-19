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

    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        """
        Generates clinical recommendations using Groq API.
        Automatically falls back to local Ollama if primary call fails.
        """
        # If API key is missing entirely, skip primary and run local Ollama directly
        if not self.primary.api_key:
            logger.warning("No Groq API Key found. Directly routing to local fallback generator (Ollama).")
            try:
                res = self.fallback.generate_answer(query, chunks)
                self.failover_engine.last_used_fallback = True
                return res
            except Exception as e:
                return f"[Generation Error - Both API Key missing and Ollama offline]: {e}"
        
        # Run failover generation engine
        return self.failover_engine.generate_answer(query, chunks)
