import json
import urllib.request
import logging
from typing import List
from rag_system.embeddings.base import BaseEmbedder

logger = logging.getLogger("LocalEmbedders")


class FastEmbedEmbedder(BaseEmbedder):
    """Local, offline CPU-based embedding generator using ONNX models."""

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        self._model = model
        self.client = None
        try:
            from fastembed import TextEmbedding
            # This downloads model files on first run (small, ~100MB)
            self.client = TextEmbedding(model_name=model)
            logger.info(f"FastEmbed initialized locally with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize FastEmbed: {e}")

    @property
    def dimension(self) -> int:
        if "small" in self._model:
            return 384
        if "nomic" in self._model:
            return 768
        return 384

    def embed_query(self, text: str) -> List[float]:
        if not self.client:
            raise RuntimeError("FastEmbed client not initialized.")
        embeddings = list(self.client.embed([text]))
        return [float(x) for x in embeddings[0]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.client:
            raise RuntimeError("FastEmbed client not initialized.")
        embeddings = list(self.client.embed(texts))
        return [[float(x) for x in emb] for emb in embeddings]


class OllamaEmbedder(BaseEmbedder):
    """Local Ollama-based text embedding generator."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.host = host.rstrip("/")
        self.model = model

    @property
    def dimension(self) -> int:
        return 768

    def embed_query(self, text: str) -> List[float]:
        return self._embed_ollama(f"search_query: {text}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_ollama(t) for t in texts]

    def _embed_ollama(self, prompt: str) -> List[float]:
        url = f"{self.host}/api/embeddings"
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("embedding", [])
