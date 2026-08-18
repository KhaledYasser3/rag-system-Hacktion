"""
=============================================================================
  RETRIEVER FRAMEWORK — Prompt & Query Builder
=============================================================================
  Preprocesses user query strings (lowercasing, whitespace cleanup,
  punctuation normalization, medical synonym expansion interface) and
  constructs structured prompts for generation.
=============================================================================
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Set
from shared.models import Query, RetrievedChunk


class SynonymExpander(ABC):
    """Abstract interface for medical domain synonym expansion."""

    @abstractmethod
    def expand(self, text: str) -> List[str]:
        """Returns list of expanded synonym terms for medical concepts in query."""
        pass


class MedicalSynonymExpander(SynonymExpander):
    """Default medical dictionary mapping common abbreviations and drug classes."""

    SYNONYM_MAP: Dict[str, List[str]] = {
        "t2d": ["type 2 diabetes", "type 2 diabetes mellitus"],
        "t1d": ["type 1 diabetes", "type 1 diabetes mellitus"],
        "dpp-4": ["dpp-4 inhibitors", "dipeptidyl peptidase-4 inhibitors", "gliptins"],
        "dpp4": ["dpp-4 inhibitors", "dipeptidyl peptidase-4 inhibitors"],
        "sglt2": ["sglt-2 inhibitors", "sodium-glucose cotransporter 2"],
        "sglt-2": ["sglt-2 inhibitors", "sodium-glucose cotransporter 2"],
        "glp-1": ["glp-1 receptor agonists", "glucagon-like peptide-1"],
        "glp1": ["glp-1 receptor agonists", "glucagon-like peptide-1"],
        "sulfonylurea": ["sulfonylureas", "glibenclamide", "gliclazide", "glimepiride"],
        "sulfonylureas": ["sulfonylurea", "glibenclamide", "gliclazide"],
        "insulin analogue": ["long-acting insulin", "short-acting insulin", "glargine", "detemir"],
        "nph": ["nph insulin", "intermediate-acting insulin", "isophane insulin"]
    }

    def expand(self, text: str) -> List[str]:
        expanded = []
        tokens = re.findall(r"\b[\w\-]+\b", text.lower())
        for token in tokens:
            if token in self.SYNONYM_MAP:
                expanded.extend(self.SYNONYM_MAP[token])
        return list(set(expanded))


class QueryProcessor:
    """Query Preprocessing pipeline performing cleaning, normalization, and expansion."""

    def __init__(self, synonym_expander: SynonymExpander | None = None):
        self.synonym_expander = synonym_expander or MedicalSynonymExpander()

    def process(self, raw_query: str) -> Query:
        """Preprocesses raw question string into a Query domain object."""
        if not raw_query or not raw_query.strip():
            raise ValueError("Query string cannot be empty.")

        cleaned = raw_query.strip()
        lowered = cleaned.lower()

        normalized = re.sub(r"\s+", " ", lowered)
        normalized = re.sub(r"[^\w\s\-\?:.,]", "", normalized).strip()

        expanded = self.synonym_expander.expand(normalized) if self.synonym_expander else []

        return Query(
            raw_query=cleaned,
            processed_query=normalized,
            normalized_query=normalized,
            expanded_terms=expanded
        )


def build_rag_prompt(query: str, retrieved_chunks: List[RetrievedChunk]) -> str:
    """
    Constructs a structured prompt instructing the LLM to generate a clinical response
    with explicit PDF page citations.
    """
    context_str = ""
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        p_start = chunk.metadata.get("page_start", "N/A")
        p_end = chunk.metadata.get("page_end", p_start)
        page_ref = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}-{p_end}"
        chapter = chunk.metadata.get("chapter", "General")
        section = chunk.metadata.get("section", "")
        
        context_str += f"--- [Source #{idx}: WHO Guidelines {page_ref} | {chapter} > {section}] ---\n"
        context_str += f"{chunk.content}\n\n"

    prompt = f"""You are an expert medical AI assistant helping physicians diagnose and treat diabetes based strictly on official WHO Guidelines.

### CONTEXT FROM WHO GUIDELINES:
{context_str}

### QUESTION / CLINICAL SCENARIO:
{query}

### INSTRUCTIONS:
1. Provide a concise, clear clinical summary and treatment recommendation.
2. Explicitly cite the exact page numbers from the WHO Guidelines for every recommendation or clinical claim (e.g., "[WHO Guidelines Page 12]").
3. If the context does not contain enough information to answer the question, state that clearly.
"""
    return prompt
