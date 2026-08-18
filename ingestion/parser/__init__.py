"""
Modular PDF Parser Package Initialization.
"""
from ingestion.parser.models import BlockType, ContentBlock, ParsedPage, ParsedDocument, AdvancedQualityTracker, QualityTracker
from ingestion.parser.config import ParserConfig
from ingestion.parser.pipeline import ParserPipeline
from ingestion.parser.backend import PDFBackend, PDFPlumberBackend
from ingestion.parser.validation.parser_validator import ParserValidator
from ingestion.parser.inspect import main as inspect_parser

def advanced_parse_pdf(pdf_path: str = "data/pdfs/9789241550284-eng.pdf"):
    """Bridge function for pipeline compatibility."""
    cfg = ParserConfig(parallel_processing=True)
    pipeline = ParserPipeline(config=cfg)
    doc_obj, tracker = pipeline.parse(pdf_path)
    return doc_obj.to_legacy_pages(), tracker

__all__ = [
    "BlockType",
    "ContentBlock",
    "ParsedPage",
    "ParsedDocument",
    "AdvancedQualityTracker",
    "QualityTracker",
    "ParserConfig",
    "ParserPipeline",
    "PDFBackend",
    "PDFPlumberBackend",
    "ParserValidator",
    "advanced_parse_pdf",
]
