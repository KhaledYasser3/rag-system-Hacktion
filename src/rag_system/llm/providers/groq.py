import os
import logging
from typing import List, Optional
from rag_system.shared.models import RetrievedChunk
from rag_system.llm.base import BaseGenerator

logger = logging.getLogger("GroqGenerator")


class GroqGenerator(BaseGenerator):
    """Cloud-based LLM Generator using Groq API (openai/gpt-oss-120b)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-oss-120b"):
        self.model_name = model
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "").strip()
        self.client = None
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                logger.info(f"Groq client initialized with model: {model}")
            except ImportError:
                logger.warning("groq package not installed. Run: pip install groq")
        else:
            logger.warning("No Groq API key provided. GroqGenerator will fail if invoked.")

    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        if not self.client:
            raise ValueError("Groq generator not initialized. Ensure GROQ_API_KEY is configured.")
        
        from rag_system.retriever.prompt_builder import build_rag_prompt
        prompt = build_rag_prompt(query, chunks)
        
        # Call Groq API completions
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model_name,
                temperature=0.2,  # Low temperature for clinical accuracy
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq generation request failed: {e}")
            raise RuntimeError(f"Groq API call failed: {e}") from e
