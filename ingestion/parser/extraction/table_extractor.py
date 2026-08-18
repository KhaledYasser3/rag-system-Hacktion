"""
=============================================================================
  MODULAR PDF PARSER — Structured Table & Glossary Extractor
=============================================================================
  Extracts tables as structured TableBlock / ContentBlock objects.
  Distinguishes real data tables from single-column Glossary boxes, guaranteeing
  that glossary term definitions are preserved as Content (NOT set to Title).
=============================================================================
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple
from ingestion.parser.models import ContentBlock, BlockType

logger = logging.getLogger("TableExtractor")


class TableExtractor:
    """Extracts tables and glossary boxes from PDF pages."""

    def extract_page_tables(
        self,
        page_obj: Any,
        page_num: int,
        chapter: str = "",
        section: str = ""
    ) -> List[ContentBlock]:
        """Extracts all tables on a page and returns list of ContentBlock objects."""
        blocks: List[ContentBlock] = []
        raw_tables = page_obj.extract_tables()

        is_glossary_context = "glossary" in (chapter + " " + section).lower()

        for idx, t in enumerate(raw_tables):
            try:
                bbox = getattr(t, "bbox", (0.0, 0.0, page_obj.width, page_obj.height))
                raw_data = t.extract()
                if not raw_data or not raw_data[0]:
                    continue

                # 1. Check if this is a single-column Glossary Box
                if is_glossary_context or self._is_single_column_glossary_box(raw_data):
                    glossary_block = self._parse_glossary_box(raw_data, page_num, bbox, idx + 1)
                    if glossary_block:
                        blocks.append(glossary_block)
                        continue

                # 2. Standard Multidimensional Data Table
                headers = [str(c or "").strip() for c in raw_data[0]]
                rows = [[str(c or "").strip() for c in row] for row in raw_data[1:]] if len(raw_data) > 1 else []

                # Format clean markdown table
                md_table = self._format_markdown_table(raw_data)
                table_title = f"Table {idx+1} Page {page_num}"

                c_block = ContentBlock(
                    block_id=f"tbl_p{page_num}_{idx+1}",
                    page_number=page_num,
                    block_type=BlockType.TABLE,
                    title=table_title,
                    content=md_table,
                    headers=headers,
                    rows=rows,
                    bbox=bbox,
                    metadata={
                        "has_missing_headers": not any(headers),
                        "row_count": len(rows),
                        "col_count": len(headers)
                    }
                )
                blocks.append(c_block)
            except Exception as e:
                logger.error(f"Failed to extract table {idx+1} on page {page_num}: {e}")

        return blocks

    def _is_single_column_glossary_box(self, raw_data: List[List[Any]]) -> bool:
        """Return True if table matrix represents a single-column box containing term + definition."""
        max_cols = max(len(row) for row in raw_data if row)
        if max_cols == 1 and len(raw_data) >= 2:
            first_cell = str(raw_data[0][0] or "").strip()
            # If first row is short term name (< 60 chars) and second row contains text definition
            if len(first_cell) < 60 and not first_cell.endswith("."):
                return True
        return False

    def _parse_glossary_box(
        self,
        raw_data: List[List[Any]],
        page_num: int,
        bbox: tuple,
        idx: int
    ) -> Optional[ContentBlock]:
        """
        Parses single-column glossary table box, strictly separating TITLE (Term Name)
        from CONTENT (Real Definition).
        """
        clean_rows = []
        for r in raw_data:
            c_text = " ".join([str(cell or "").strip() for cell in r if cell]).strip()
            if c_text:
                clean_rows.append(c_text)

        if not clean_rows:
            return None

        # Row 0 is the Term Name (Title)
        term_name = clean_rows[0]

        # Row 1..N is the REAL Definition (Content)
        if len(clean_rows) > 1:
            definition_text = "\n".join(clean_rows[1:])
            parse_warning = None
        else:
            # Term exists but definition was missing or unparsed
            definition_text = ""
            parse_warning = "definition_not_detected"

        return ContentBlock(
            block_id=f"glos_p{page_num}_{idx}",
            page_number=page_num,
            block_type=BlockType.GLOSSARY_ENTRY,
            title=term_name,
            content=definition_text,
            bbox=bbox,
            metadata={
                "term": term_name,
                "is_table_box": True,
                "parse_warning": parse_warning
            }
        )

    def _format_markdown_table(self, table_data: List[List[Any]]) -> str:
        """Formats list-of-lists table into clean markdown."""
        if not table_data or not table_data[0]:
            return ""

        max_cols = max(len(row) for row in table_data)
        clean_table = []
        for row in table_data:
            clean_row = [str(c or "").replace("\n", " ").strip() for c in row]
            while len(clean_row) < max_cols:
                clean_row.append("")
            clean_table.append(clean_row)

        headers = clean_table[0]
        headers = [col if col else f"Column {i+1}" for i, col in enumerate(headers)]
        rows = clean_table[1:]

        md = "\n| " + " | ".join(headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        for row in rows:
            md += "| " + " | ".join(row) + " |\n"
        return md
