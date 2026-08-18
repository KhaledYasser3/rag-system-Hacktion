"""
Extraction package init.
"""
from ingestion.parser.extraction.text_extractor import TextExtractor
from ingestion.parser.extraction.table_extractor import TableExtractor
from ingestion.parser.extraction.figure_extractor import FigureExtractor
from ingestion.parser.extraction.ocr_extractor import OCRExtractor

__all__ = [
    "TextExtractor",
    "TableExtractor",
    "FigureExtractor",
    "OCRExtractor",
]
