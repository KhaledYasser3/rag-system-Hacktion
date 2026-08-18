"""
=============================================================================
  MODULAR PDF PARSER — Unit Test Suite
=============================================================================
  Verifies parser modularity, table extraction, figure extraction, heading
  classification, and glossary data integrity (ensuring title != definition).
=============================================================================
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.parser.config import ParserConfig
from ingestion.parser.models import ParsedDocument, ParsedPage, ContentBlock, BlockType
from ingestion.parser.extraction.table_extractor import TableExtractor
from ingestion.parser.extraction.figure_extractor import FigureExtractor
from ingestion.parser.structure.heading_detector import HeadingDetector
from ingestion.parser.cleaning.text_cleaner import TextCleaner
from ingestion.parser.validation.parser_validator import ParserValidator
from ingestion.parser.pipeline import ParserPipeline


class MockPDFPage:
    """Mock PDFPageBackend for testing extractors."""
    def __init__(self, width=600, height=800, raw_tables=None, raw_images=None, text=""):
        self.width = width
        self.height = height
        self._tables = raw_tables or []
        self._images = raw_images or []
        self._text = text

    def extract_tables(self):
        class MockTable:
            def __init__(self, data):
                self._data = data
                self.bbox = (50, 50, 550, 200)
            def extract(self):
                return self._data
        return [MockTable(t) for t in self._tables]

    def get_images(self):
        return self._images

    def extract_text(self, bbox=None):
        return self._text

    def crop(self, bbox):
        return self


class TestModularParser(unittest.TestCase):

    def setUp(self):
        self.validator = ParserValidator()
        self.cleaner = TextCleaner()
        self.heading_detector = HeadingDetector()
        self.table_extractor = TableExtractor()

    def test_glossary_term_and_real_definition(self):
        """CRITICAL: Verify Glossary term has REAL definition and title != content."""
        raw_table = [
            ["Type 1 diabetes"],
            ["Diabetes caused by destruction of pancreatic beta-cells, resulting in insulin deficiency."]
        ]
        page = MockPDFPage(raw_tables=[raw_table])
        blocks = self.table_extractor.extract_page_tables(page, page_num=8, chapter="Glossary", section="Definitions")

        self.assertEqual(len(blocks), 1)
        b = blocks[0]

        # 1. Block type must be GLOSSARY_ENTRY
        self.assertEqual(b.block_type, BlockType.GLOSSARY_ENTRY)

        # 2. Title MUST be term name
        self.assertEqual(b.title, "Type 1 diabetes")

        # 3. Content MUST contain REAL definition (NOT equal to title)
        self.assertNotEqual(b.content.strip(), b.title.strip())
        self.assertIn("destruction of pancreatic beta-cells", b.content)

    def test_glossary_validator_catches_fake_definition(self):
        """Verify validator flags any glossary block where content == title."""
        bad_block = ContentBlock(
            block_id="b_bad",
            page_number=8,
            block_type=BlockType.GLOSSARY_ENTRY,
            title="Type 1 diabetes",
            content="Type 1 diabetes", # Corrupted definition
            bbox=(0, 0, 100, 100)
        )
        page = ParsedPage(page_number=8, width=600, height=800, blocks=[bad_block])
        doc = ParsedDocument(document_id="test", title="Test", source_filename="test.pdf", pages=[page])

        is_valid, diagnostics = self.validator.validate(doc)
        self.assertFalse(is_valid)
        self.assertTrue(any(d["error_type"] == "glossary_term_equals_definition" for d in diagnostics))

    def test_table_headers_and_rows_preserved(self):
        """Verify standard multidimensional data tables preserve headers and rows."""
        raw_table = [
            ["Drug", "Daily Dose", "Cost"],
            ["Metformin", "2000 mg", "Low"],
            ["Gliclazide", "160 mg", "Low"]
        ]
        page = MockPDFPage(raw_tables=[raw_table])
        blocks = self.table_extractor.extract_page_tables(page, page_num=15, chapter="Treatment", section="Medicines")

        self.assertEqual(len(blocks), 1)
        b = blocks[0]

        self.assertEqual(b.block_type, BlockType.TABLE)
        self.assertEqual(b.headers, ["Drug", "Daily Dose", "Cost"])
        self.assertEqual(len(b.rows), 2)
        self.assertIn("Metformin", b.content)
        self.assertIn("Gliclazide", b.content)

    def test_heading_detection(self):
        """Verify multi-signal heading detector."""
        is_h, level, prefix = self.heading_detector.detect_heading("Executive Summary", 14.0, 10.0, True)
        self.assertTrue(is_h)
        self.assertEqual(level, 1)

        is_h, level, prefix = self.heading_detector.detect_heading("3.1 Hypoglycaemic agents", 11.5, 10.0, True)
        self.assertTrue(is_h)
        self.assertEqual(level, 2)

    def test_text_cleaner_preserves_content(self):
        """Verify text cleaner repairs hyphenation without deleting content."""
        raw = "glu-\ncose levels in patients"
        cleaned = self.cleaner.clean_text(raw)
        self.assertEqual(cleaned, "glucose levels in patients")


if __name__ == "__main__":
    unittest.main()
