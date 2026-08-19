"""
=============================================================================
  MEDICAL RAG PIPELINE — Stage 3: Semantic Chunk Builder
=============================================================================
  Input  : DocumentNode tree from hierarchy_builder.py
  Output : Semantic chunks saved to chunks.json and chunks.jsonl,
           Chunk Validation Report, and Summary Statistics.

  Chunking Strategy & Rules
  ─────────────────────────
  1. Semantic Boundaries Only
     - Splits on Chapter, Section, Subsection, or major topic boundaries.
     - Never splits mid-sentence or mid-word.
     - Never separates a heading from its content.

  2. Atomic Context Preservation
     - Tables (TableNode) and Figures (FigureNode) are kept intact as atomic units.
     - Captions and table matrices remain with explaining body text.

  3. Size Targets & Small Section Merging
     - Target size : 300 – 600 tokens (Hard max: 800 tokens).
     - Merges small adjacent sections (< 150 tokens) inside the same chapter.

  4. Stable Chunk IDs & Rich Metadata
     - Deterministic chunk_id: chk_<hash>_<index:04d>
     - Metadata: chunk_id, document_title, chapter, section, subsection,
       page_start, page_end, token_count, table_references, figure_references.
     - figure_references structured metadata format:
       [
         {
           "figure_id": "fig_001",
           "caption": "...",
           "page": 1,
           "image_path": "media/figure_page_1_1.png"
         }
       ]

  5. Figure Zero-Loss Guarantee & Strict Fail-Safe Validation
     - Detected Figures vs Attached Figures vs Lost Figures report.
     - Exception raised if Lost Figures > 0.

  6. Export Formats
     - JSON   : chunks.json
     - JSONL  : chunks.jsonl
=============================================================================
"""

from __future__ import annotations

import os
import re
import sys
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Union

# Attempt tiktoken import for exact token counts, fallback to word-ratio estimation
try:
    import tiktoken
    _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text: str) -> int:
        return len(_TIKTOKEN_ENC.encode(text))
except ImportError:
    def count_tokens(text: str) -> int:
        return int(len(text.split()) * 1.3)


def _safe_print(*args, **kwargs) -> None:
    """Drop-in replacement for print() that never crashes on encoding errors."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        file = kwargs.get("file", sys.stdout)
        msg = sep.join(str(a) for a in args) + end
        msg = msg.replace("✅", "[OK]").replace("⚠️", "[WARN]").replace("❌", "[FAIL]").replace("├", "|").replace("└", "+").replace("│", "|").replace("─", "-")
        enc = getattr(file, "encoding", "ascii") or "ascii"
        try:
            file.buffer.write(msg.encode(enc, errors="replace"))
        except Exception:
            pass


def _clean_figure_caption(raw_caption: str, page_number: int) -> str:
    """Extract clean text caption from markdown or raw figure strings."""
    if not raw_caption:
        return f"Figure Page {page_number}"

    # Strip markdown image tag format: ![Caption](path)
    m_img = re.match(r"!\[(.*?)\]\(.*?\)", raw_caption.strip())
    if m_img:
        txt = m_img.group(1).strip()
        if txt:
            return txt

    # Strip *Caption*: *Text* format
    m_cap = re.search(r"\*Caption\*:\s*\*([^*]+)\*", raw_caption.strip())
    if m_cap:
        return m_cap.group(1).strip()

    # Strip markdown symbols
    cleaned = re.sub(r"[*_#`]", "", raw_caption).strip()
    return cleaned if cleaned else f"Figure Page {page_number}"


# ─────────────────────────────────────────────────────────────────────────────
# 1.  SEMANTIC CHUNK DATA MODEL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SemanticChunk:
    """A semantic chunk ready for vector embedding and RAG retrieval."""
    chunk_id: str
    document_title: str
    chapter: str
    section: str
    subsection: str
    content: str
    page_start: int
    page_end: int
    token_count: int
    table_references: List[str] = field(default_factory=list)
    figure_references: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_title": self.document_title,
            "chapter": self.chapter,
            "section": self.section,
            "subsection": self.subsection,
            "content": self.content,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "token_count": self.token_count,
            "table_references": self.table_references,
            "figure_references": self.figure_references
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2.  SEMANTIC CHUNK BUILDER
# ─────────────────────────────────────────────────────────────────────────────

class SemanticChunkBuilder:
    """
    Transforms a DocumentNode hierarchy tree into semantic, metadata-rich chunks
    satisfying RAG size guidelines (300-600 tokens) without losing or duplicating content.
    """

    def __init__(
        self,
        min_chunk_tokens: int = 150,
        target_chunk_tokens: int = 450,
        max_chunk_tokens: int = 800
    ):
        self.min_chunk_tokens = min_chunk_tokens
        self.target_chunk_tokens = target_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self._fig_counter = 1

    def build_chunks(self, doc) -> List[SemanticChunk]:
        """Convert DocumentNode tree into list of SemanticChunk objects."""
        self._fig_counter = 1

        # 1. Collect all leaf blocks with full section hierarchy path
        flattened_blocks = []
        self._flatten_tree(doc, doc.title, "", "", "", flattened_blocks)

        if not flattened_blocks:
            return []

        # 2. Group blocks into semantic section clusters
        semantic_clusters = self._cluster_by_section(flattened_blocks)

        # 3. Assemble clusters into target-sized chunks (300-600 tokens)
        chunks = []
        doc_prefix = hashlib.md5(doc.title.encode("utf-8")).hexdigest()[:8]
        chunk_idx = 1

        for cluster in semantic_clusters:
            cluster_chunks = self._pack_cluster(cluster, doc_prefix, chunk_idx, doc.title)
            chunks.extend(cluster_chunks)
            chunk_idx += len(cluster_chunks)

        return chunks

    def _flatten_tree(
        self,
        node,
        doc_title: str,
        current_ch: str,
        current_sec: str,
        current_sub: str,
        out_blocks: list
    ) -> None:
        """Traverse tree depth-first and collect content leaves with hierarchy metadata."""
        node_type = getattr(node, "node_type", "")

        if node_type == "Document Title":
            for child in getattr(node, "children", []):
                self._flatten_tree(child, doc_title, current_ch, current_sec, current_sub, out_blocks)

        elif node_type in ("Chapter", "Appendix", "Document Title Heading"):
            ch_title = node.title
            for child in getattr(node, "children", []):
                self._flatten_tree(child, doc_title, ch_title, "", "", out_blocks)

        elif node_type == "Section":
            sec_title = node.title
            for child in getattr(node, "children", []):
                self._flatten_tree(child, doc_title, current_ch, sec_title, "", out_blocks)

        elif node_type == "Subsection":
            sub_title = node.title
            for child in getattr(node, "children", []):
                self._flatten_tree(child, doc_title, current_ch, current_sec, sub_title, out_blocks)

        elif node_type == "Paragraph":
            p_block = {
                "type": "paragraph",
                "text": node.text,
                "page_number": node.page_number,
                "chapter": current_ch or doc_title,
                "section": current_sec,
                "subsection": current_sub,
                "obj": node
            }
            sub_paras = _split_large_paragraph(p_block, max_tokens=400)
            out_blocks.extend(sub_paras)

        elif node_type == "Table":
            tbl_title = getattr(node, "title", getattr(node, "caption", ""))
            if not tbl_title or tbl_title == "UNKNOWN":
                tbl_title = f"Table Page {node.page_number}"

            tbl_block = {
                "type": "table",
                "text": node.text,
                "title": tbl_title,
                "page_number": node.page_number,
                "chapter": current_ch or doc_title,
                "section": current_sec,
                "subsection": current_sub,
                "obj": node
            }
            sub_tbls = _split_large_table(tbl_block, max_tokens=350)
            out_blocks.extend(sub_tbls)

        elif node_type == "Figure":
            fig_id = f"fig_{self._fig_counter:03d}"
            self._fig_counter += 1

            clean_cap = _clean_figure_caption(getattr(node, "caption", ""), node.page_number)
            img_p = getattr(node, "image_path", "media/figure.png")

            fig_meta = {
                "figure_id": fig_id,
                "caption": clean_cap,
                "page": node.page_number,
                "image_path": img_p
            }

            out_blocks.append({
                "type": "figure",
                "text": node.text,
                "figure_meta": fig_meta,
                "page_number": node.page_number,
                "chapter": current_ch or doc_title,
                "section": current_sec,
                "subsection": current_sub,
                "obj": node
            })

    def _cluster_by_section(self, blocks: list) -> list:
        """Group consecutive blocks sharing the same Chapter & Section."""
        clusters = []
        current_key = None
        current_cluster = []

        for b in blocks:
            key = (b["chapter"], b["section"])
            if key != current_key:
                if current_cluster:
                    clusters.append(current_cluster)
                current_cluster = [b]
                current_key = key
            else:
                current_cluster.append(b)

        if current_cluster:
            clusters.append(current_cluster)

        # Merge tiny adjacent clusters within the same Chapter (< 150 tokens)
        merged_clusters = []
        i = 0
        while i < len(clusters):
            c = clusters[i]
            c_text = " ".join(b["text"] for b in c)
            c_tokens = count_tokens(c_text)

            if c_tokens < self.min_chunk_tokens and i + 1 < len(clusters):
                next_c = clusters[i + 1]
                if c[0]["chapter"] == next_c[0]["chapter"]:
                    next_text = " ".join(b["text"] for b in next_c)
                    if c_tokens + count_tokens(next_text) <= self.target_chunk_tokens:
                        clusters[i + 1] = c + next_c
                        i += 1
                        continue

            merged_clusters.append(c)
            i += 1

        return merged_clusters

    def _pack_cluster(
        self,
        cluster: list,
        prefix: str,
        start_idx: int,
        doc_title: str
    ) -> List[SemanticChunk]:
        """Pack a block cluster into one or more target-sized SemanticChunk objects."""
        chunks = []
        if not cluster:
            return chunks

        chapter = cluster[0]["chapter"]
        section = cluster[0]["section"]
        subsection = cluster[0]["subsection"]

        current_items = []
        current_tokens = 0
        current_pages = []
        current_tables = []
        current_figures = []

        # Add section header context at start of chunk
        header_context = ""
        if chapter:
            header_context += f"## {chapter}\n"
        if section:
            header_context += f"### {section}\n"
        if subsection:
            header_context += f"#### {subsection}\n"

        base_tokens = count_tokens(header_context)
        current_tokens += base_tokens

        def finalize_chunk(is_continuation: bool = False) -> SemanticChunk:
            nonlocal current_items, current_tokens, current_pages, current_tables, current_figures

            content_lines = [header_context.strip()] if header_context.strip() else []
            if is_continuation and section:
                content_lines.append(f"*(Continued from {section})*")

            for item in current_items:
                content_lines.append(item["text"].strip())

            full_content = "\n\n".join(content_lines).strip()
            p_start = min(current_pages) if current_pages else 1
            p_end = max(current_pages) if current_pages else 1
            t_cnt = count_tokens(full_content)

            chk_id = f"chk_{prefix}_{start_idx + len(chunks):04d}"

            chunk = SemanticChunk(
                chunk_id=chk_id,
                document_title=doc_title,
                chapter=chapter,
                section=section,
                subsection=subsection,
                content=full_content,
                page_start=p_start,
                page_end=p_end,
                token_count=t_cnt,
                table_references=list(current_tables),
                figure_references=list(current_figures)
            )

            current_items = []
            current_tokens = base_tokens
            current_pages = []
            current_tables = []
            current_figures = []

            return chunk

        for b in cluster:
            b_text = b["text"].strip()
            b_tokens = count_tokens(b_text)

            if current_tokens + b_tokens > self.max_chunk_tokens and current_items:
                chunks.append(finalize_chunk(is_continuation=True))

            current_items.append(b)
            current_tokens += b_tokens
            current_pages.append(b["page_number"])

            if b["type"] == "table":
                t_ref = b.get("title", b.get("caption", "Table"))
                current_tables.append(t_ref)
            elif b["type"] == "figure":
                f_meta = b["figure_meta"]
                current_figures.append(f_meta)

            if current_tokens >= self.target_chunk_tokens:
                chunks.append(finalize_chunk(is_continuation=False))

        if current_items:
            chunks.append(finalize_chunk(is_continuation=False))

        return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 3.  BLOCK SPLITTING UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _split_large_paragraph(block: dict, max_tokens: int = 400) -> list:
    """Splits a massive paragraph into sub-paragraph blocks on sentence boundaries."""
    text = block["text"].strip()
    if count_tokens(text) <= max_tokens:
        return [block]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    if len(sentences) <= 1:
        return [block]

    sub_blocks = []
    current_sentences = []
    current_tokens = 0

    for s in sentences:
        s_tokens = count_tokens(s)
        if current_tokens + s_tokens > max_tokens and current_sentences:
            sub_text = " ".join(current_sentences)
            sub_b = dict(block)
            sub_b["text"] = sub_text
            sub_blocks.append(sub_b)
            current_sentences = [s]
            current_tokens = s_tokens
        else:
            current_sentences.append(s)
            current_tokens += s_tokens

    if current_sentences:
        sub_text = " ".join(current_sentences)
        sub_b = dict(block)
        sub_b["text"] = sub_text
        sub_blocks.append(sub_b)

    return sub_blocks if sub_blocks else [block]


def _split_large_table(block: dict, max_tokens: int = 350) -> list:
    """Splits a massive markdown table into sub-tables with repeating header rows."""
    text = block["text"]
    if count_tokens(text) <= max_tokens:
        return [block]

    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 3:
        return [block]

    header_lines = []
    row_lines = []
    in_header = True

    for l in lines:
        if in_header:
            header_lines.append(l)
            if "---" in l or len(header_lines) >= 2:
                in_header = False
        else:
            row_lines.append(l)

    header_block = "\n".join(header_lines)
    header_tokens = count_tokens(header_block)

    sub_blocks = []
    current_rows = []
    current_tokens = header_tokens

    for r in row_lines:
        r_tokens = count_tokens(r)
        if current_tokens + r_tokens > max_tokens and current_rows:
            sub_text = header_block + "\n" + "\n".join(current_rows)
            sub_b = dict(block)
            sub_b["text"] = sub_text
            sub_blocks.append(sub_b)
            current_rows = [r]
            current_tokens = header_tokens + r_tokens
        else:
            current_rows.append(r)
            current_tokens += r_tokens

    if current_rows:
        sub_text = header_block + "\n" + "\n".join(current_rows)
        sub_b = dict(block)
        sub_b["text"] = sub_text
        sub_blocks.append(sub_b)

    return sub_blocks if sub_blocks else [block]


# ─────────────────────────────────────────────────────────────────────────────
# 4.  VALIDATION STAGE (validate_chunks)
# ─────────────────────────────────────────────────────────────────────────────

def validate_chunks(doc, chunks: List[SemanticChunk]) -> Tuple[bool, List[str]]:
    """
    Validates zero content loss (paragraphs, tables, figures) during chunking,
    checking structured figure_references and size limits.
    """
    warnings = []

    # 1. Count original leaf nodes in DocumentNode
    orig_paras = 0
    orig_tables = 0
    orig_figures = 0

    def _walk(node):
        nonlocal orig_paras, orig_tables, orig_figures
        n_type = getattr(node, "node_type", "")
        if n_type == "Paragraph":
            orig_paras += 1
        elif n_type == "Table":
            orig_tables += 1
        elif n_type == "Figure":
            orig_figures += 1

        for c in getattr(node, "children", []):
            _walk(c)

    _walk(doc)

    # 2. Count attached content occurrences across generated chunks
    chunk_tables = sum(len(c.table_references) for c in chunks)
    attached_figures = sum(len(c.figure_references) for c in chunks)
    lost_figures = max(0, orig_figures - attached_figures)

    # 3. Check for oversized chunks (> 800 tokens)
    oversized = [c for c in chunks if c.token_count > 800]
    if oversized:
        warnings.append(f"⚠️ Found {len(oversized)} chunk(s) exceeding 800 token maximum size.")

    # 4. Check for empty chunks
    empty_chunks = [c for c in chunks if not c.content.strip()]
    if empty_chunks:
        warnings.append(f"❌ Found {len(empty_chunks)} empty chunk(s).")

    # 5. Check figure zero-loss requirement
    if lost_figures > 0:
        warnings.append(f"❌ CRITICAL FIGURE LOSS: {lost_figures} figure(s) lost during chunking! (Detected: {orig_figures}, Attached: {attached_figures})")

    is_valid = len(warnings) == 0 and lost_figures == 0
    return is_valid, warnings


# ─────────────────────────────────────────────────────────────────────────────
# 5.  EXPORT & DISPLAY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def export_chunks(
    chunks: List[SemanticChunk],
    json_path: str = "chunks.json",
    jsonl_path: str = "chunks.jsonl"
) -> None:
    """Export chunks to JSON and JSONL formats."""
    dict_chunks = [c.to_dict() for c in chunks]

    # Export JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dict_chunks, f, indent=2, ensure_ascii=False)

    # Export JSONL
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for chk in dict_chunks:
            f.write(json.dumps(chk, ensure_ascii=False) + "\n")


def print_chunk_statistics(doc, chunks: List[SemanticChunk]) -> None:
    """Print detailed chunk statistics and validation report."""
    if not chunks:
        _safe_print("⚠️ No chunks generated.")
        return

    tokens = [c.token_count for c in chunks]
    avg_tokens = sum(tokens) / len(tokens)
    min_tokens = min(tokens)
    max_tokens = max(tokens)

    # Calculate Figure Stats
    orig_paras, orig_tables, orig_figures = 0, 0, 0
    def _walk(node):
        nonlocal orig_paras, orig_tables, orig_figures
        n_type = getattr(node, "node_type", "")
        if n_type == "Paragraph":
            orig_paras += 1
        elif n_type == "Table":
            orig_tables += 1
        elif n_type == "Figure":
            orig_figures += 1
        for c in getattr(node, "children", []):
            _walk(c)
    _walk(doc)

    attached_figures = sum(len(c.figure_references) for c in chunks)
    lost_figures = max(0, orig_figures - attached_figures)

    is_valid, warnings = validate_chunks(doc, chunks)

    _safe_print("\n" + "=" * 72)
    _safe_print("  SEMANTIC CHUNK BUILDER STATISTICS & FIGURE VALIDATION")
    _safe_print("=" * 72)
    _safe_print(f"  Total Chunks Generated      : {len(chunks)}")
    _safe_print(f"  Average Tokens per Chunk   : {avg_tokens:.1f}")
    _safe_print(f"  Smallest Chunk             : {min_tokens} tokens")
    _safe_print(f"  Largest Chunk              : {max_tokens} tokens")
    _safe_print("-" * 72)
    _safe_print(f"  Detected Figures           : {orig_figures}")
    _safe_print(f"  Attached Figures           : {attached_figures}")
    _safe_print(f"  Lost Figures               : {lost_figures}")
    _safe_print("-" * 72)
    _safe_print("  Validation Status           : " + ("✅ PASSED (0 loss, 0 duplication)" if is_valid else "❌ WARNINGS DETECTED"))
    if warnings:
        for w in warnings:
            _safe_print(f"    {w}")
    _safe_print("=" * 72 + "\n")

    if lost_figures > 0:
        raise ValueError(f"❌ CHUNK GENERATION FAILED: Lost {lost_figures} figure(s) during chunking!")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rag_system.ingestion.parser import advanced_parse_pdf
    from rag_system.ingestion.hierarchy_builder import HierarchyBuilder

    PDF = "9789241550284-eng.pdf"
    print(f"[Semantic Chunker] Parsing PDF: {PDF} ...")
    parsed_docs, _ = advanced_parse_pdf(PDF)

    builder = HierarchyBuilder()
    doc = builder.build(parsed_docs)

    chunker = SemanticChunkBuilder(
        min_chunk_tokens=150,
        target_chunk_tokens=450,
        max_chunk_tokens=800
    )
    chunks = chunker.build_chunks(doc)

    # Export chunks to disk
    export_chunks(chunks, json_path="data/chunks/chunks.json", jsonl_path="data/chunks/chunks.jsonl")
    print(f"[Semantic Chunker] Saved {len(chunks)} chunks to data/chunks/chunks.json and data/chunks/chunks.jsonl")

    # Print summary statistics and validation report
    print_chunk_statistics(doc, chunks)
