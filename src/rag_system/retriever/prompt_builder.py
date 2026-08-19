"""
=============================================================================
  RETRIEVER FRAMEWORK — Prompt & Query Builder
=============================================================================
  Preprocesses user query strings (whitespace cleanup, normalization) and
  constructs structured prompts for generation.
  Supports automatic language detection so the LLM responds in the same
  language the user asked in (Arabic → Arabic answer, English → English answer).
=============================================================================
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Dict
from rag_system.shared.models import Query, RetrievedChunk


# ─── Language Detection ───────────────────────────────────────────────────────

# Unicode Arabic block: \u0600–\u06FF
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def detect_language(text: str) -> str:
    """
    Returns 'arabic' if the text contains Arabic characters,
    otherwise returns 'english'.
    """
    arabic_chars = len(_ARABIC_RE.findall(text))
    total_alpha = len(re.findall(r"[a-zA-Z\u0600-\u06FF]", text))
    if total_alpha == 0:
        return "english"
    return "arabic" if arabic_chars / total_alpha > 0.3 else "english"


# ─── Synonym Expansion ────────────────────────────────────────────────────────

class SynonymExpander(ABC):
    """Abstract interface for domain synonym expansion."""

    @abstractmethod
    def expand(self, text: str) -> List[str]:
        """Returns list of expanded synonym terms for concepts in query."""
        pass


class NullExpander(SynonymExpander):
    """No-op expander. The embedding model handles semantics better than a static dictionary."""

    def expand(self, text: str) -> List[str]:
        return []


# ─── Query Processor ─────────────────────────────────────────────────────────

class QueryProcessor:
    """
    Query Preprocessing pipeline.
    Preserves original casing (for better embedding quality on acronyms/proper nouns).
    Only strips leading/trailing whitespace and normalises internal spaces.
    """

    def __init__(self, synonym_expander: SynonymExpander | None = None):
        self.synonym_expander = synonym_expander or NullExpander()

    def process(self, raw_query: str) -> Query:
        """Preprocesses raw question string into a Query domain object."""
        if not raw_query or not raw_query.strip():
            raise ValueError("Query string cannot be empty.")

        cleaned = raw_query.strip()

        # Preserve original casing — only collapse whitespace
        normalized = re.sub(r"\s+", " ", cleaned).strip()

        expanded = self.synonym_expander.expand(normalized) if self.synonym_expander else []

        return Query(
            raw_query=cleaned,
            processed_query=normalized,   # same casing as original
            normalized_query=normalized,
            expanded_terms=expanded
        )


# ─── RAG Prompt Builder ───────────────────────────────────────────────────────

def build_rag_prompt(query: str, retrieved_chunks: List[RetrievedChunk]) -> str:
    """
    Constructs a structured clinical RAG prompt for the LLM.

    Features:
    - Calm, professional diabetes information assistant persona.
    - Explicit medical safety bounds (no prescribing, diagnosing, or dose recommendations).
    - Multi-lingual translation directive (English sources -> natural Arabic answers).
    - Hardened grounding checks and fallback responses for missing information.
    - Retrieval-aware chunk evaluation rules (term matching is not evidence).
    - Structured output formats with justified confidence levels (High/Medium/Low).
    - Precise citation grounding using source-derived index tokens.
    """
    lang = detect_language(query)

    # Build the numbered source context block
    context_str = ""
    if retrieved_chunks:
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            p_start = chunk.metadata.get("page_start", "?")
            p_end   = chunk.metadata.get("page_end", p_start)
            chapter = chunk.metadata.get("chapter", "")
            section = chunk.metadata.get("section", "")

            page_ref = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}–{p_end}"
            location = " › ".join(filter(None, [chapter, section]))
            header = f"[Source #{idx} | {page_ref}" + (f" | {location}" if location else "") + "]"

            context_str += f"--- {header} ---\n{chunk.content.strip()}\n\n"
    else:
        context_str = "(No relevant source chunks were retrieved for this question.)\n"

    # Language-specific instructions
    if lang == "arabic":
        lang_instruction = (
            "CRITICAL: The user's question is in ARABIC. "
            "You MUST respond entirely in clear, natural Arabic. "
            "Translate English source chunks accurately to Arabic, preserving their original medical meaning. "
            "Write the English medical term in parentheses next to its Arabic translation when helpful (e.g. السكري من النوع الثاني (Type 2 Diabetes))."
        )
    else:
        lang_instruction = (
            "Respond in clear, professional English."
        )

    prompt = f"""You are a calm, helpful, and professional medical information assistant specialized in diabetes-related information. Your purpose is to help users understand diabetes-related information from the provided medical documents.

=== MEDICAL SAFETY CONSTRAINTS ===
- You must NOT diagnose patients, prescribe medications, or recommend changing medication/insulin doses.
- You must NOT replace a doctor or healthcare professional. Do not provide unsupported medical advice.
- Provide educational, source-grounded information.
- For potentially urgent situations, clearly encourage appropriate professional medical evaluation without inventing specific emergency protocols.
- Never tell a patient to start/stop medications or ignore severe symptoms unless the source explicitly supports it, and frame it clearly as a guideline recommendation rather than a personalized instruction.

=== LANGUAGE DIRECTION ===
{lang_instruction}

=== SOURCE CHUNKS ===
{context_str}
=== END OF SOURCES ===

=== USER QUESTION ===
{query}

=== INSTRUCTIONS ===
1. AUTHORITATIVE SOURCE OF TRUTH: Answer ONLY from the retrieved contexts. Do not use outside knowledge. 
   - If the retrieved context is completely insufficient or unrelated, do NOT guess or hallucinate. You must output:
     In English: "I couldn't find enough information about this in the provided diabetes guidelines to answer confidently."
     In Arabic: "المعلومات المتاحة في المستندات المرفقة لا تكفي للإجابة عن السؤال ده بشكل موثوق."
2. RETRIEVAL-AWARE ANSWERING: Inspect all chunks. Terminology matching does not automatically equal evidence. Identify which chunks directly support the answer vs. chunks that are only related background. Use the directly supporting chunks as citation sources.
3. CITATION ACCURACY: Support every factual claim derived from the documents with a source citation using `[Source #N]`. If claims come from different chunks, cite them separately. Never invent page numbers, section names, or citation IDs.
4. FACT VS. INTERPRETATION: Distinguish explicit facts from inferences. For facts, use phrases like "The guideline recommends...". For inferences/interpretations, use "The available evidence suggests...". Never state "WHO recommends..." unless explicitly written in the source.
5. DO NOT OVERANSWER: Keep responses direct and proportional to the query. Do not provide unrelated clinical context.
6. OUTPUT FORMAT: Expose ONLY the structured fields below. Do not expose internal reasoning, chain-of-thought, ranking logic, or scores to the user.

Choose the format below that matches the query's complexity:

[Format A - For simple or direct factual questions]
Answer:
[direct answer]

Confidence:
[High / Medium / Low] (Briefly justify. HIGH: explicitly stated in source, no ambiguity. MEDIUM: strongly supported but requires minor interpretation or synthesis. LOW: evidence is incomplete, indirect, or ambiguous. Do NOT calculate confidence using vector similarity scores alone.)

Source:
[Source #N] (with page reference)

[Format B - For complex questions requiring synthesis of multiple points]
Answer:
[direct answer]

Key points:
- [point 1]
- [point 2]

Confidence:
[High / Medium / Low] (Briefly justify)

Source:
[Source #N] (with page references)
"""
    return prompt
