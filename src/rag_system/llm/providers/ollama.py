import json
import urllib.request
import logging
from typing import List
from rag_system.shared.models import RetrievedChunk
from rag_system.llm.base import BaseGenerator

logger = logging.getLogger("OllamaGenerator")


class OllamaGenerator(BaseGenerator):
    """Local LLM Generator using local Ollama model (e.g. llama3/mistral)."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3"):
        self.host = host.rstrip("/")
        self.model = model

    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        from rag_system.retriever.prompt_builder import build_rag_prompt
        
        prompt = build_rag_prompt(query, chunks)
        
        # Auto-detect if host is a Google Colab Cloudflare/Ngrok Tunnel API
        if "trycloudflare.com" in self.host or "ngrok-free.app" in self.host or "ngrok.io" in self.host:
            logger.info("Tunnel URL detected. Routing query to OpenAI-compatible chat completions endpoint.")
            url = f"{self.host}/v1/chat/completions"
            payload = json.dumps({
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 512,
                "temperature": 0.2
            }).encode("utf-8")
        else:
            # Default local Ollama endpoint
            url = f"{self.host}/api/generate"
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "choices" in data:
                # Parse OpenAI-style FastAPI completions response
                return data["choices"][0]["message"]["content"].strip()
            return data.get("response", "").strip()
