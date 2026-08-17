import unittest
from professional_parser import (
    format_table_as_markdown,
    classify_table,
    semantic_section_classifier,
    HierarchicalOutlineStack,
    QualityTracker
)

class TestMedicalRAGParser(unittest.TestCase):
    
    def test_format_table_as_markdown_standard(self):
        """Test standard tabular data formatting to Markdown."""
        table_data = [
            ["Drug", "Dose", "Frequency"],
            ["Metformin", "500mg", "Once daily"],
            ["Gliclazide", "80mg", "Twice daily"]
        ]
        expected = "\n| Drug | Dose | Frequency |\n| --- | --- | --- |\n| Metformin | 500mg | Once daily |\n| Gliclazide | 80mg | Twice daily |\n\n"
        result = format_table_as_markdown(table_data)
        self.assertEqual(result, expected)

    def test_format_table_as_markdown_with_nones(self):
        """Test formatting table data containing None values (e.g. from merged cells)."""
        table_data = [
            ["Drug", "Dose", None],
            ["Insulin Glargine", "10 units", "Subcutaneous"],
            [None, "Adjust dose", "Based on glycaemia"]
        ]
        result = format_table_as_markdown(table_data)
        self.assertIn("| Drug | Dose | Column 3 |", result)
        self.assertIn("| Insulin Glargine | 10 units | Subcutaneous |", result)
        self.assertIn("|  | Adjust dose | Based on glycaemia |", result)

    def test_classify_table_medication(self):
        """Test table classifier tags medication tables correctly."""
        headers = ["Drug Name", "Insulin Dose", "Indications"]
        rows = [["Metformin", "500 mg", "Adult type 2 DM"]]
        classification = classify_table(headers, rows)
        self.assertEqual(classification, "Medication Table")

    def test_classify_table_diagnostic(self):
        """Test table classifier tags diagnostic tables correctly."""
        headers = ["Criteria", "Fasting Glucose", "HbA1c Threshold"]
        rows = [["Diabetes Mellitus", ">= 7.0 mmol/L", ">= 6.5%"]]
        classification = classify_table(headers, rows)
        self.assertEqual(classification, "Diagnostic Table")

    def test_classify_table_general(self):
        """Test table classifier tags general context tables correctly."""
        headers = ["Contributor", "Affiliation", "Role"]
        rows = [["Dr. Smith", "WHO", "Reviewer"]]
        classification = classify_table(headers, rows)
        self.assertEqual(classification, "General Table")

    def test_semantic_section_classifier_evidence(self):
        """Test semantic classifier categorizes evidence/literature review sections."""
        content = "We conducted a literature review across PubMed for clinical evidence of glimepiride."
        sem_class = semantic_section_classifier(content)
        self.assertEqual(sem_class, "Clinical Evidence & Studies")

    def test_semantic_section_classifier_insulin(self):
        """Test semantic classifier categorizes insulin dosing sections."""
        content = "Start insulin glargine or detemir dose at 10 units once daily."
        sem_class = semantic_section_classifier(content)
        self.assertEqual(sem_class, "Medication & Insulin Dosing Protocol")

    def test_outline_stack_hierarchy(self):
        """Test heading outline stack updates and pops correctly to track document chapter structure."""
        stack = HierarchicalOutlineStack()
        stack.set_document_title("WHO Diabetes Guidelines 2018")
        
        # Add Chapter
        stack.update_heading(1, "Chapter 1: Background")
        meta = stack.get_metadata()
        self.assertEqual(meta["chapter"], "Chapter 1: Background")
        self.assertEqual(meta["section"], "Unknown")
        
        # Add Section
        stack.update_heading(2, "1.1 Scope and Aim")
        meta = stack.get_metadata()
        self.assertEqual(meta["chapter"], "Chapter 1: Background")
        self.assertEqual(meta["section"], "1.1 Scope and Aim")
        self.assertEqual(meta["subsection"], "Unknown")
        
        # Add Subsection
        stack.update_heading(3, "1.1.1 Target Population")
        meta = stack.get_metadata()
        self.assertEqual(meta["subsection"], "1.1.1 Target Population")
        
        # Add a new Chapter (should pop all lower-level section headings)
        stack.update_heading(1, "Chapter 2: Recommendations")
        meta = stack.get_metadata()
        self.assertEqual(meta["chapter"], "Chapter 2: Recommendations")
        self.assertEqual(meta["section"], "Unknown")
        self.assertEqual(meta["subsection"], "Unknown")

if __name__ == "__main__":
    unittest.main()
