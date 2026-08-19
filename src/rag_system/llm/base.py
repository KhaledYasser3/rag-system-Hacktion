from abc import ABC, abstractmethod
from typing import List
from rag_system.shared.models import RetrievedChunk

class BaseGenerator(ABC):
    """Abstract base class representing LLM text generation engines."""

    @abstractmethod
    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        """Assembles prompt and queries LLM to return medical response."""
        pass
