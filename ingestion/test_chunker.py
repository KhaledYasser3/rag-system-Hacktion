"""
=============================================================================
  STRUCTURE-AWARE CHUNKING MODULE — Unit Test Suite
=============================================================================
"""

import os
import sys
import unittest

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.chunking.config import ChunkingConfig
from ingestion.chunking.models import ContentType, StructuralBlock, StructureAwareChunk
from ingestion.chunking.classifiers.content_classifier import ContentClassifier
from ingestion.chunking.context.context_enricher import ContextEnricher
from ingestion.chunking.validators.chunk_validator import ChunkValidator
from ingestion.chunking.strategies.semantic import SemanticChunkingStrategy
from ingestion.chunking.strategies.glossary import GlossaryChunkingStrategy
from ingestion.chunking.strategies.table import TableChunkingStrategy
from ingestion.chunking.strategies.list_strategy import ListChunkingStrategy
from ingestion.chunking.utils.token_utils import WordRatioTokenCounter
from ingestion.chunking.pipeline import ChunkingPipeline
from ingestion.hierarchy_builder import DocumentNode, HeadingNode, ParagraphNode, TableNode, FigureNode


class TestStructureAwareChunker(unittest.TestCase):

    def setUp(self):
        self.config = ChunkingConfig(
            target_chunk_tokens=300,
            max_chunk_tokens=400,
            min_chunk_tokens=50,
            overlap_tokens=30
        )
        self.token_counter = WordRatioTokenCounter()
        self.classifier = ContentClassifier()
        self.enricher = ContextEnricher(self.config)
        self.validator = ChunkValidator(self.config)

    def test_classifier(self):
        """Test deterministic content classification."""
        # Glossary section block
        p_glossary = ParagraphNode(
            text="Type 1 diabetes\nDiabetes caused by beta-cell destruction.",
            page_number=7,
            chapter_title="Glossary"
        )
        c_type = self.classifier.classify(p_glossary, "Glossary", "Definitions", "")
        self.assertEqual(c_type, ContentType.GLOSSARY_ENTRY)

        # Table node
        tbl = TableNode(
            title="Medications",
            headers=["Drug", "Dose"],
            rows=[["Metformin", "500mg"]],
            text="| Drug | Dose |\n| --- | --- |\n| Metformin | 500mg |",
            page_number=15
        )
        c_type = self.classifier.classify(tbl, "Treatment", "Medicines", "")
        self.assertEqual(c_type, ContentType.TABLE)

    def test_glossary_atomicity(self):
        """Verify glossary entries are kept as independent atomic chunks."""
        strategy = GlossaryChunkingStrategy()
        block = StructuralBlock(
            block_id="b1",
            content_type=ContentType.GLOSSARY_ENTRY,
            text="Type 1 diabetes\nDefinition of type 1 diabetes.\n\nType 2 diabetes\nDefinition of type 2 diabetes.\n\nSGLT-2 inhibitors\nDefinition of SGLT-2.",
            page_number=7,
            chapter="Glossary",
            section="Definitions"
        )
        context = {"doc_prefix": "test", "doc_title": "WHO Guidelines", "chunk_counter": 1}
        chunks = strategy.chunk(block, context, self.config, self.token_counter)

        # Must produce 3 independent chunks (1 per glossary term)
        self.assertEqual(len(chunks), 3)

        # Check terms are independent
        terms = [c.title for c in chunks]
        self.assertIn("Type 1 diabetes", terms)
        self.assertIn("Type 2 diabetes", terms)
        self.assertIn("SGLT-2 inhibitors", terms)

        # Ensure Type 1 diabetes chunk does NOT contain SGLT-2 inhibitors definition
        t1_chunk = next(c for c in chunks if "Type 1" in c.title)
        self.assertNotIn("SGLT-2", t1_chunk.content)

    def test_table_header_preservation(self):
        """Verify large table row splits preserve table headers in every sub-chunk."""
        strategy = TableChunkingStrategy()
        headers = ["Drug", "Mechanism", "Recommendation"]
        # Generate many rows to exceed max_chunk_tokens
        rows = [[f"Drug {i}", f"Effect {i}", f"Rec {i}"] for i in range(1, 40)]
        table_text = "| " + " | ".join(headers) + " |\n| --- | --- | --- |\n"
        for r in rows:
            table_text += "| " + " | ".join(r) + " |\n"

        block = StructuralBlock(
            block_id="b_tbl",
            content_type=ContentType.TABLE,
            text=table_text,
            page_number=15,
            chapter="Treatment",
            section="Medications",
            title="Diabetes Medication Recommendations",
            headers=headers,
            rows=rows
        )
        context = {"doc_prefix": "test", "doc_title": "WHO Guidelines", "chunk_counter": 1}

        small_cfg = ChunkingConfig(max_chunk_tokens=100)
        chunks = strategy.chunk(block, context, small_cfg, self.token_counter)

        self.assertGreater(len(chunks), 1)

        # Verify EVERY sub-chunk retains the column headers
        for c in chunks:
            self.assertIn("Drug", c.content)
            self.assertIn("Mechanism", c.content)
            self.assertIn("Recommendation", c.content)

    def test_context_enrichment(self):
        """Verify embedding_text is contextualized separate from original content."""
        chunk = StructureAwareChunk(
            chunk_id="chk_001",
            document_title="WHO Guidelines",
            chapter="Treatment Guidelines",
            section="Second-Line Agents",
            subsection="Sulfonylureas",
            content_type=ContentType.PARAGRAPH,
            title="Sulfonylureas Dosing",
            content="In patients with type 2 diabetes, sulfonylureas are recommended...",
            embedding_text="",
            page_start=14,
            page_end=14,
            token_count=50
        )
        enriched = self.enricher.enrich(chunk)

        # Check embedding_text contains hierarchy headers
        self.assertIn("Chapter: Treatment Guidelines", enriched.embedding_text)
        self.assertIn("Section: Second-Line Agents", enriched.embedding_text)
        self.assertIn("Subsection: Sulfonylureas", enriched.embedding_text)

        # Check content remains original clean content
        self.assertEqual(enriched.content, "In patients with type 2 diabetes, sulfonylureas are recommended...")

    def test_chunk_validator(self):
        """Test validator catches empty or corrupted chunks."""
        good_chunk = StructureAwareChunk(
            chunk_id="chk_001",
            document_title="WHO Guidelines",
            chapter="Intro",
            section="",
            subsection="",
            content_type=ContentType.PARAGRAPH,
            title="Intro",
            content="Valid content text.",
            embedding_text="Chapter: Intro\n\nContent:\nValid content text.",
            page_start=1,
            page_end=1,
            token_count=10
        )
        is_valid, issues = self.validator.validate([good_chunk])
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)

        # Test empty content chunk
        bad_chunk = dict(good_chunk.__dict__)
        bad_chunk["content"] = ""
        bad_obj = StructureAwareChunk(**bad_chunk)

        strict_val = ChunkValidator(ChunkingConfig(strict_validation=False))
        is_valid_bad, bad_issues = strict_val.validate([bad_obj])
        self.assertFalse(is_valid_bad)
        self.assertGreater(len(bad_issues), 0)

    def test_full_pipeline_on_synthetic_tree(self):
        """Test end-to-end ChunkingPipeline on a synthetic DocumentNode hierarchy tree."""
        doc = DocumentNode(title="WHO Diabetes Guidelines")

        # Chapter 1: Glossary
        ch_glos = HeadingNode(title="Glossary", level=1, node_type_name="Chapter", page_number=7)
        ch_glos.add_child(ParagraphNode(
            text="Type 1 diabetes\nDiabetes characterized by beta-cell destruction.\n\nSGLT-2 inhibitors\nSodium-glucose co-transporters type 2 inhibitors.",
            page_number=7,
            chapter_title="Glossary"
        ))
        doc.add_child(ch_glos)

        # Chapter 2: Treatment
        ch_treat = HeadingNode(title="Treatment Recommendations", level=1, node_type_name="Chapter", page_number=12)
        sec_2line = HeadingNode(title="Second-Line Treatment", level=2, node_type_name="Section", page_number=13)
        sec_2line.add_child(ParagraphNode(
            text="Metformin is the first-line treatment. When metformin fails, add a sulfonylurea or SGLT-2 inhibitor.",
            page_number=13,
            chapter_title="Treatment Recommendations",
            section_title="Second-Line Treatment"
        ))
        ch_treat.add_child(sec_2line)
        doc.add_child(ch_treat)

        pipeline = ChunkingPipeline(self.config)
        chunks = pipeline.run(doc)

        self.assertGreater(len(chunks), 0)

        # Check glossary chunk
        glos_chunks = [c for c in chunks if c.content_type == ContentType.GLOSSARY_ENTRY]
        self.assertGreater(len(glos_chunks), 0)
        self.assertEqual(glos_chunks[0].chapter, "Glossary")

        # Check section boundary separation
        treat_chunks = [c for c in chunks if c.chapter == "Treatment Recommendations"]
        self.assertGreater(len(treat_chunks), 0)
        self.assertEqual(treat_chunks[0].section, "Second-Line Treatment")


if __name__ == "__main__":
    unittest.main()
