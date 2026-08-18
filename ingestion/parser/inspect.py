"""
=============================================================================
  MODULAR PDF PARSER — Debug Inspection CLI
=============================================================================
  Allows developers to inspect extracted ParsedDocument blocks, page by page,
  verifying content fidelity and zero-information-loss guarantees.

  Usage:
      python -m ingestion.parser.inspect <pdf_path> [--page PAGE_NUM]
=============================================================================
"""

from __future__ import annotations

import sys
import os
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ingestion.parser.pipeline import ParserPipeline
from ingestion.parser.config import ParserConfig
from shared.utils import safe_print


def main():
    parser = argparse.ArgumentParser(description="Inspect intermediate ParsedDocument output from Modular PDF Parser.")
    parser.add_argument("pdf_path", nargs="?", default=os.path.join("data", "pdfs", "9789241550284-eng.pdf"), help="Path to PDF file.")
    parser.add_argument("--page", type=int, default=None, help="Specific page number to inspect.")

    args = parser.parse_args()
    pdf_path = args.pdf_path

    if not os.path.exists(pdf_path):
        safe_print(f"❌ Error: PDF file not found at '{pdf_path}'.")
        sys.exit(1)

    safe_print(f"[Parser Inspector] Parsing PDF document: '{pdf_path}'...")
    cfg = ParserConfig(parallel_processing=True)
    pipeline = ParserPipeline(config=cfg)

    doc, tracker = pipeline.parse(pdf_path)

    safe_print("\n" + "=" * 75)
    safe_print(f" PARSED DOCUMENT SUMMARY: {doc.title}")
    safe_print("=" * 75)
    safe_print(f" Total Pages Parsed : {len(doc.pages)}")
    safe_print(f" Figures Extracted  : {tracker.figures_extracted}")
    safe_print(f" Tables Extracted   : {tracker.tables_extracted}")
    safe_print(f" Glossary Entries   : {tracker.glossary_entries_extracted}")
    safe_print(f" Execution Duration : {tracker.elapsed_time():.2f} seconds")
    safe_print("=" * 75)

    target_pages = [doc.pages[args.page - 1]] if args.page and 1 <= args.page <= len(doc.pages) else doc.pages

    for p in target_pages:
        if args.page is None and p.page_number not in (7, 8, 9, 12, 13):
            continue

        safe_print(f"\n" + "-" * 75)
        safe_print(f" PAGE {p.page_number} (Blocks: {len(p.blocks)})")
        safe_print("-" * 75)

        for b in p.blocks:
            safe_print(f"\n[Block ID: {b.block_id} | Type: {b.block_type.value.upper()} | Page: {b.page_number}]")
            safe_print(f"Title / Term : {b.title if b.title else '(None)'}")
            safe_print(f"Content      :")
            content_preview = b.content.strip()
            if len(content_preview) > 300:
                safe_print(content_preview[:300] + "\n...")
            else:
                safe_print(content_preview)
            safe_print(f"BBox         : {b.bbox}")
            if b.metadata:
                safe_print(f"Metadata     : {b.metadata}")

    safe_print("\n" + "=" * 75)
    safe_print(f" Exported full structured document -> '{cfg.output_parsed_json}'")
    safe_print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
