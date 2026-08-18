"""
=============================================================================
  MODULAR PDF PARSER — Structural Block Builder
=============================================================================
  Assembles raw page lines, tables, and figures into normalized ContentBlock
  objects. Ensures Glossary entries strictly separate TITLE (Term Name) from
  CONTENT (Real Definition Text).
=============================================================================
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Dict, Any, Tuple
from ingestion.parser.models import ContentBlock, BlockType
from ingestion.parser.structure.heading_detector import HeadingDetector
from ingestion.parser.structure.hierarchy import HierarchyTracker


class BlockBuilder:
    """Assembles layout elements into structured ContentBlock models."""

    def __init__(self):
        self.heading_detector = HeadingDetector()

    def build_page_blocks(
        self,
        words: List[Dict[str, Any]],
        tables: List[ContentBlock],
        figures: List[ContentBlock],
        page_num: int,
        hierarchy_tracker: HierarchyTracker,
        repeating_headers: set = None,
        repeating_footers: set = None
    ) -> List[ContentBlock]:
        """Assembles words and pre-extracted tables/figures into ordered page blocks."""
        repeating_headers = repeating_headers or set()
        repeating_footers = repeating_footers or set()

        # 1. Filter header/footer words
        cleaned_words = []
        for w in words:
            txt = w.get("text", "").strip()
            if txt not in repeating_headers and txt not in repeating_footers:
                cleaned_words.append(w)

        # 2. Group words into lines
        lines = self._group_words_into_lines(cleaned_words)

        # Determine median body font size
        body_size = 10.0
        all_sizes = [round(w.get("size", 10.0), 1) for w in cleaned_words if w.get("size")]
        if all_sizes:
            body_size = Counter(all_sizes).most_common(1)[0][0]

        # 3. Process text lines into ContentBlocks
        text_blocks: List[ContentBlock] = []
        block_idx = 1

        for line in lines:
            line_sorted = sorted(line, key=lambda x: x["x0"])
            text = " ".join([w["text"] for w in line_sorted]).strip()
            if not text:
                continue

            avg_size = sum(w.get("size", body_size) for w in line_sorted) / len(line_sorted)
            font_names = [w.get("fontname", "").lower() for w in line_sorted if w.get("fontname")]
            is_bold = any(any(bk in fn for bk in ["bold", "heavy", "black", "semibold"]) for fn in font_names)

            is_heading, level, prefix = self.heading_detector.detect_heading(text, avg_size, body_size, is_bold)

            meta = hierarchy_tracker.get_current_metadata()
            is_glossary_sec = "glossary" in (meta["chapter"] + " " + meta["section"]).lower()

            bbox = (
                line_sorted[0]["x0"],
                line_sorted[0]["top"],
                line_sorted[-1]["x1"],
                line_sorted[-1]["bottom"]
            )

            if is_heading:
                clean_h = text.lstrip("#").strip()
                hierarchy_tracker.update_heading(level, clean_h)
                text_blocks.append(ContentBlock(
                    block_id=f"hd_p{page_num}_{block_idx}",
                    page_number=page_num,
                    block_type=BlockType.HEADING,
                    title=clean_h,
                    content=f"## {clean_h}",
                    bbox=bbox,
                    reading_order=block_idx
                ))
            elif is_glossary_sec and self._is_glossary_term_line(text):
                # Glossary Term line: term name = title, definition follows
                term_name = text.strip()
                text_blocks.append(ContentBlock(
                    block_id=f"glos_p{page_num}_{block_idx}",
                    page_number=page_num,
                    block_type=BlockType.GLOSSARY_ENTRY,
                    title=term_name,
                    content="", # Will be filled by definition text if present
                    bbox=bbox,
                    reading_order=block_idx,
                    metadata={"term": term_name}
                ))
            else:
                text_blocks.append(ContentBlock(
                    block_id=f"txt_p{page_num}_{block_idx}",
                    page_number=page_num,
                    block_type=BlockType.PARAGRAPH,
                    title="",
                    content=text,
                    bbox=bbox,
                    reading_order=block_idx
                ))
            block_idx += 1

        # 4. Attach definitions to Glossary term blocks if split across lines
        self._link_glossary_definitions(text_blocks)

        # 5. Filter out text falling inside table bounding boxes
        table_bboxes = [t.bbox for t in tables]
        filtered_text_blocks = []
        for tb in text_blocks:
            inside_table = False
            for t_bbox in table_bboxes:
                if tb.bbox[1] >= t_bbox[1] - 2 and tb.bbox[3] <= t_bbox[3] + 2:
                    inside_table = True
                    break
            if not inside_table:
                filtered_text_blocks.append(tb)

        # 6. Merge all blocks into single sorted page list
        all_blocks = sorted(filtered_text_blocks + tables + figures, key=lambda b: (b.reading_order, b.bbox[1]))
        return all_blocks

    def _group_words_into_lines(self, words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Groups sorted words into horizontal lines."""
        lines = []
        current_line = []
        for w in words:
            if not current_line:
                current_line.append(w)
            else:
                if abs(current_line[-1]["top"] - w["top"]) < 4:
                    current_line.append(w)
                else:
                    lines.append(current_line)
                    current_line = [w]
        if current_line:
            lines.append(current_line)
        return lines

    def _is_glossary_term_line(self, text: str) -> bool:
        """Return True if line looks like a standalone Glossary term header."""
        s = text.strip()
        return len(s) < 60 and not s.endswith(".") and not s.startswith(("-", "*"))

    def _link_glossary_definitions(self, blocks: List[ContentBlock]) -> None:
        """Links following definition paragraph blocks to preceding Glossary term blocks."""
        i = 0
        while i < len(blocks):
            b = blocks[i]
            if b.block_type == BlockType.GLOSSARY_ENTRY and not b.content:
                # Look ahead for definition blocks
                def_parts = []
                j = i + 1
                while j < len(blocks) and blocks[j].block_type == BlockType.PARAGRAPH:
                    def_parts.append(blocks[j].content.strip())
                    blocks[j].block_type = BlockType.UNKNOWN # Mark merged
                    j += 1
                if def_parts:
                    b.content = "\n".join(def_parts)
                else:
                    # Fallback if definition was unparsed
                    b.metadata["parse_warning"] = "definition_not_detected"
            i += 1

        # Remove merged blocks
        blocks[:] = [b for b in blocks if b.block_type != BlockType.UNKNOWN]
