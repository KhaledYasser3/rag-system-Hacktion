from abc import ABC, abstractmethod
from typing import List

class BaseEmbedder(ABC):
    """Abstract base class representing text embedding engines."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the output vector dimension size (e.g. 768 or 1024)."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embeds a single search query."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of document chunks (batched)."""
        pass
