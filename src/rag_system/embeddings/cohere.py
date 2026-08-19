import os
import logging
from typing import List, Optional
from rag_system.embeddings.base import BaseEmbedder

logger = logging.getLogger("CohereEmbedder")


class CohereEmbedder(BaseEmbedder):
    """Cohere API text embedding generator."""

    def __init__(self, api_key: Optional[str] = None, model: str = "embed-english-v3.0"):
        self._model = model
        self.api_key = api_key or os.environ.get("COHERE_API_KEY", "")
        self.client = None
        if self.api_key:
            try:
                import cohere
                self.client = cohere.Client(api_key=self.api_key)
                logger.info(f"Cohere client initialized successfully with model: {model}")
            except ImportError:
                logger.warning("Cohere package not installed. Run: pip install cohere")
        else:
            logger.warning("No Cohere API key provided. CohereEmbedder will fail if invoked.")

    @property
    def dimension(self) -> int:
        # standard english-v3 and multilingual-v3 output 1024 dimensions
        if "light" in self._model:
            return 384
        return 1024

    def embed_query(self, text: str) -> List[float]:
        if not self.client:
            raise ValueError("Cohere client not initialized. Ensure COHERE_API_KEY is configured.")
        
        response = self.client.embed(
            texts=[text],
            model=self._model,
            input_type="search_query",
            embedding_types=["float"]
        )
        return response.embeddings.float[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.client:
            raise ValueError("Cohere client not initialized. Ensure COHERE_API_KEY is configured.")
        
        response = self.client.embed(
            texts=texts,
            model=self._model,
            input_type="search_document",
            embedding_types=["float"]
        )
        return response.embeddings.float
