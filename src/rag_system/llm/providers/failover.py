import logging
from typing import List
from rag_system.shared.models import RetrievedChunk
from rag_system.llm.base import BaseGenerator

logger = logging.getLogger("FailoverGenerator")


class FailoverGenerator(BaseGenerator):
    """
    Hybrid high-availability generator.
    Attempts to call primary cloud generator, and falls back to
    local Ollama if primary fails or quota is exhausted.
    """

    def __init__(self, primary: BaseGenerator, fallback: BaseGenerator):
        self.primary = primary
        self.fallback = fallback
        self.last_used_fallback = False

    def generate_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        try:
            logger.info("Attempting generation using primary generator...")
            res = self.primary.generate_answer(query, chunks)
            self.last_used_fallback = False
            logger.info("Primary generator succeeded.")
            return res
        except Exception as e:
            logger.warning(f"Primary generator failed ({e}). Attempting fallback to local generator...")
            try:
                res = self.fallback.generate_answer(query, chunks)
                self.last_used_fallback = True
                logger.info("Fallback generator succeeded.")
                return res
            except Exception as fe:
                err_msg = f"Both primary and fallback generators failed! (Primary: {e}) (Fallback: {fe})"
                logger.critical(err_msg)
                raise RuntimeError(err_msg)
