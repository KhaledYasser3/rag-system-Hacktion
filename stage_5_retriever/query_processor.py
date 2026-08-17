"""
=============================================================================
  STAGE 5: RETRIEVER FRAMEWORK — Query Processor
=============================================================================
  Preprocesses user query strings (lowercasing, whitespace cleanup,
  punctuation normalization, medical synonym expansion interface).
=============================================================================
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Set
from stage_5_retriever.models import Query


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

        # Lowercase normalization
        lowered = cleaned.lower()

        # Punctuation & extra space cleanup
        normalized = re.sub(r"\s+", " ", lowered)
        normalized = re.sub(r"[^\w\s\-\?:.,]", "", normalized).strip()

        # Medical Synonym Expansion
        expanded = self.synonym_expander.expand(normalized) if self.synonym_expander else []

        return Query(
            raw_query=cleaned,
            processed_query=normalized,
            normalized_query=normalized,
            expanded_terms=expanded
        )
