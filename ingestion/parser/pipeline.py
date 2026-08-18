"""
=============================================================================
  MODULAR PDF PARSER — Pipeline Orchestrator
=============================================================================
  High-level flow:
  PDF Backend
        ↓
  Margin & Layout Detection
        ↓
  Extractors (Text, Table, Figure, OCR)
        ↓
  Block Builder & Structure Assembly
        ↓
  Text Cleaning
        ↓
  Validation
        ↓
  Structured ParsedDocument
=============================================================================
"""

from __future__ import annotations

import os
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, List, Dict, Any, Tuple

from ingestion.parser.config import ParserConfig
from ingestion.parser.models import ParsedDocument, ParsedPage, ContentBlock, BlockType, AdvancedQualityTracker
from ingestion.parser.backend import PDFBackend, PDFPlumberBackend
from ingestion.parser.extraction.text_extractor import TextExtractor
from ingestion.parser.extraction.table_extractor import TableExtractor
from ingestion.parser.extraction.figure_extractor import FigureExtractor
from ingestion.parser.extraction.ocr_extractor import OCRExtractor
from ingestion.parser.layout.margin_detector import MarginDetector
from ingestion.parser.layout.column_detector import ColumnDetector
from ingestion.parser.layout.reading_order import ReadingOrderSorter
from ingestion.parser.structure.hierarchy import HierarchyTracker
from ingestion.parser.structure.block_builder import BlockBuilder
from ingestion.parser.cleaning.text_cleaner import TextCleaner
from ingestion.parser.validation.parser_validator import ParserValidator

logger = logging.getLogger("ParserPipeline")


def _process_single_page_worker(
    pdf_path: str,
    page_num: int,
    margin_meta: dict,
    doc_title: str,
    config: ParserConfig
) -> Dict[str, Any]:
    """Worker function executed in parallel for single page processing."""
    backend = PDFPlumberBackend()
    backend.open(pdf_path)

    try:
        page = backend.get_page(page_num)
        table_extractor = TableExtractor()
        figure_extractor = FigureExtractor(media_dir=config.media_dir, min_width=config.figure_min_width, min_height=config.figure_min_height)
        ocr_extractor = OCRExtractor(languages=config.ocr_languages)
        text_cleaner = TextCleaner()
        hierarchy_tracker = HierarchyTracker(doc_title=doc_title)
        block_builder = BlockBuilder()
        reading_sorter = ReadingOrderSorter()
        column_detector = ColumnDetector(min_gap_pts=config.min_column_gap_pts)

        # 1. Dynamic Margin Cropping
        header_lim = margin_meta.get("header_limit", 50.0)
        footer_lim = margin_meta.get("footer_limit", 790.0)
        page_height_ref = margin_meta.get("page_height", page.height)

        h_ratio = header_lim / page_height_ref
        f_ratio = (page_height_ref - footer_lim) / page_height_ref

        crop_box = (0.0, page.height * h_ratio, page.width, page.height * (1.0 - f_ratio))
        cropped_page = page.crop(crop_box)

        # 2. Extract Tables & Figures
        tables = table_extractor.extract_page_tables(cropped_page, page_num) if config.extract_tables else []
        figures = figure_extractor.extract_page_figures(cropped_page, page_num) if config.extract_figures else []

        # 3. Check for Scanned Page OCR Fallback
        raw_text = page.extract_text(crop_box)
        clean_raw = text_cleaner.clean_text(raw_text)

        is_ocr = False
        if len(clean_raw) < config.min_ocr_text_length and config.enable_ocr and ocr_extractor.is_available():
            ocr_text = ocr_extractor.extract_region(page, (0.0, 0.0, page.width, page.height))
            if ocr_text:
                is_ocr = True
                ocr_block = ContentBlock(
                    block_id=f"ocr_p{page_num}_1",
                    page_number=page_num,
                    block_type=BlockType.PARAGRAPH,
                    title="OCR Fallback Content",
                    content=text_cleaner.clean_text(ocr_text),
                    bbox=(0.0, 0.0, page.width, page.height)
                )
                parsed_page = ParsedPage(
                    page_number=page_num,
                    width=page.width,
                    height=page.height,
                    blocks=[ocr_block],
                    metadata={"is_ocr": True, "layout_type": "scanned_image"}
                )
                return parsed_page.to_dict()

        # 4. Extract Words and apply Reading Order Sorter
        words = cropped_page.extract_words()
        sorted_words = reading_sorter.sort_words(words, (0.0, crop_box[1], page.width, crop_box[3]))

        # 5. Build Structural Blocks
        blocks = block_builder.build_page_blocks(
            sorted_words,
            tables,
            figures,
            page_num,
            hierarchy_tracker,
            margin_meta.get("repeating_headers"),
            margin_meta.get("repeating_footers")
        )

        # 6. Apply Text Cleaning to all blocks
        for b in blocks:
            b.content = text_cleaner.clean_text(b.content)

        col_split = column_detector.detect_columns(cropped_page)
        layout_type = "two_column" if col_split else "single_column"
        page_meta = hierarchy_tracker.get_current_metadata()
        page_meta["is_ocr"] = is_ocr
        page_meta["layout_type"] = layout_type

        parsed_page = ParsedPage(
            page_number=page_num,
            width=page.width,
            height=page.height,
            blocks=blocks,
            metadata=page_meta
        )
        return parsed_page.to_dict()
    finally:
        backend.close()


class ParserPipeline:
    """Production Pipeline Orchestrator for Modular PDF Parsing."""

    def __init__(self, config: Optional[ParserConfig] = None, backend: Optional[PDFBackend] = None):
        self.config = config or ParserConfig()
        self.backend = backend or PDFPlumberBackend()
        self.validator = ParserValidator()
        self.margin_detector = MarginDetector(num_samples=self.config.margin_sample_pages)

    def parse(self, pdf_path: str) -> Tuple[ParsedDocument, AdvancedQualityTracker]:
        """Parses PDF document into a structured ParsedDocument and tracker object."""
        logger.info(f"Initializing Modular PDF Parser Pipeline for '{pdf_path}'...")
        tracker = AdvancedQualityTracker()
        tracker.start()

        if not os.path.exists(pdf_path):
            tracker.stop()
            raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

        self.backend.open(pdf_path)
        total_pages = self.backend.total_pages
        tracker.total_pages = total_pages

        # 1. Detect dynamic margin bounds across sample pages
        margin_meta = self.margin_detector.detect_margins(self.backend) if self.config.detect_headers_footers else {}

        doc_title = os.path.basename(pdf_path)
        first_page = self.backend.get_page(1)
        first_words = first_page.extract_words()
        if first_words:
            largest = max(first_words, key=lambda w: w.get("size", 10.0))
            title_words = [w["text"] for w in first_words if abs(w.get("size", 10.0) - largest.get("size", 10.0)) < 2]
            doc_title = " ".join(title_words)

        self.backend.close()

        # 2. Page Parsing Execution (Parallel or Sequential)
        page_nums = list(range(1, total_pages + 1))
        parsed_page_dicts = []

        if self.config.parallel_processing and total_pages > 3:
            with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = [
                    executor.submit(_process_single_page_worker, pdf_path, num, margin_meta, doc_title, self.config)
                    for num in page_nums
                ]
                for f in futures:
                    parsed_page_dicts.append(f.result())
        else:
            for num in page_nums:
                parsed_page_dicts.append(_process_single_page_worker(pdf_path, num, margin_meta, doc_title, self.config))

        # 3. Construct ParsedDocument model
        parsed_pages: List[ParsedPage] = []
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]

        for p_dict in sorted(parsed_page_dicts, key=lambda x: x["page_number"]):
            blocks = []
            for b_dict in p_dict.get("blocks", []):
                block = ContentBlock(
                    block_id=b_dict["block_id"],
                    page_number=b_dict["page_number"],
                    block_type=BlockType(b_dict["block_type"]),
                    title=b_dict.get("title", ""),
                    content=b_dict.get("content", ""),
                    headers=b_dict.get("headers", []),
                    rows=b_dict.get("rows", []),
                    bbox=tuple(b_dict.get("bbox", (0, 0, 0, 0))),
                    reading_order=b_dict.get("reading_order", 0),
                    metadata=b_dict.get("metadata", {})
                )
                blocks.append(block)

                if block.block_type == BlockType.GLOSSARY_ENTRY:
                    tracker.glossary_entries_extracted += 1
                elif block.block_type == BlockType.TABLE:
                    tracker.tables_extracted += 1
                elif block.block_type == BlockType.FIGURE:
                    tracker.figures_extracted += 1

            p_obj = ParsedPage(
                page_number=p_dict["page_number"],
                width=p_dict["width"],
                height=p_dict["height"],
                blocks=blocks,
                metadata=p_dict.get("metadata", {})
            )
            parsed_pages.append(p_obj)
            tracker.parsed_pages += 1

        doc_obj = ParsedDocument(
            document_id=doc_id,
            title=doc_title,
            source_filename=os.path.basename(pdf_path),
            pages=parsed_pages,
            metadata={"source_path": pdf_path}
        )

        # 4. Validation
        is_valid, diagnostics = self.validator.validate(doc_obj)
        tracker.errors.extend(diagnostics)

        # 5. Export JSON intermediate artifact if configured
        if self.config.output_parsed_json:
            os.makedirs(os.path.dirname(self.config.output_parsed_json), exist_ok=True)
            with open(self.config.output_parsed_json, "w", encoding="utf-8") as f:
                json.dump(doc_obj.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Exported intermediate parsed document to '{self.config.output_parsed_json}'.")

        tracker.stop()
        tracker.generate_report()
        return doc_obj, tracker
