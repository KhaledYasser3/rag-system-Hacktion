import os
import logging
from typing import List, Optional
from rag_system.shared.models import RetrievedChunk
from rag_system.llm.base import BaseGenerator

logger = logging.getLogger("GeminiGenerator")


class GeminiGenerator(BaseGenerator):
    """Cloud-based LLM Generator using Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.model_name = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.client_model = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client_model = genai.GenerativeModel(model)
                logger.info(f"Gemini client initialized with model: {model}")
            except ImportError:
                logger.warning("google-generativeai package not installed.")
        else:
            logger.warning("No Gemini API key provided. GeminiGenerator will fail if invoked.")

    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        if not self.client_model:
            raise ValueError("Gemini generator not initialized. Ensure GEMINI_API_KEY is configured.")
        
        from rag_system.retriever.prompt_builder import build_rag_prompt
        prompt = build_rag_prompt(query, chunks)
        response = self.client_model.generate_content(prompt)
        return response.text.strip()
