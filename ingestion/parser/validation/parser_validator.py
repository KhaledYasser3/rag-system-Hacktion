"""
=============================================================================
  MODULAR PDF PARSER — Parser Validator
=============================================================================
  Validates ParsedDocument structures, flagging data integrity issues like
  lost glossary definitions or orphan table rows.
=============================================================================
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any
from ingestion.parser.models import ParsedDocument, BlockType

logger = logging.getLogger("ParserValidator")


class ParserValidator:
    """Validation suite verifying ParsedDocument fidelity and integrity."""

    def validate(self, doc: ParsedDocument) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Executes validation suite on ParsedDocument.
        Returns (is_valid_bool, list_of_diagnostic_dicts).
        """
        diagnostics: List[Dict[str, Any]] = []

        if not doc.pages:
            diagnostics.append({
                "component": "ParserValidator",
                "page": 0,
                "block_id": "doc",
                "error_type": "empty_document",
                "message": "ParsedDocument contains no pages.",
                "severity": "error"
            })
            return False, diagnostics

        for p in doc.pages:
            for b in p.blocks:
                b_prefix = f"Page {p.page_number} Block {b.block_id}"

                # 1. Glossary Data Integrity Check (CRITICAL)
                if b.block_type == BlockType.GLOSSARY_ENTRY:
                    clean_title = b.title.strip().lower()
                    clean_content = b.content.strip().lower()

                    if clean_title == clean_content and clean_title != "":
                        diagnostics.append({
                            "component": "ParserValidator",
                            "page": p.page_number,
                            "block_id": b.block_id,
                            "error_type": "glossary_term_equals_definition",
                            "message": f"{b_prefix}: Definition is incorrectly equal to term name ('{b.title}'). Definition was lost!",
                            "severity": "error"
                        })
                    elif not b.content or not b.content.strip():
                        diagnostics.append({
                            "component": "ParserValidator",
                            "page": p.page_number,
                            "block_id": b.block_id,
                            "error_type": "missing_glossary_definition",
                            "message": f"{b_prefix}: Glossary term '{b.title}' has an empty definition.",
                            "severity": "warning"
                        })

                # 2. Table Integrity Check
                elif b.block_type == BlockType.TABLE:
                    if not b.content or not b.content.strip():
                        diagnostics.append({
                            "component": "ParserValidator",
                            "page": p.page_number,
                            "block_id": b.block_id,
                            "error_type": "empty_table_content",
                            "message": f"{b_prefix}: Table block has empty markdown content.",
                            "severity": "warning"
                        })

        has_errors = any(d["severity"] == "error" for d in diagnostics)
        is_valid = not has_errors

        if diagnostics:
            for diag in diagnostics:
                log_msg = f"[{diag['severity'].upper()}] {diag['component']} (Page {diag['page']}): {diag['message']}"
                if diag["severity"] == "error":
                    logger.error(log_msg)
                else:
                    logger.warning(log_msg)

        return is_valid, diagnostics
