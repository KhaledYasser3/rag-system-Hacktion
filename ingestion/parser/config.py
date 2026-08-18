"""
=============================================================================
  MODULAR PDF PARSER — Configuration Module
=============================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ParserConfig:
    """Centralized, injectable configuration parameters for the Modular PDF Parser."""
    enable_ocr: bool = True
    ocr_languages: str = "eng+ara"
    tesseract_cmd: Optional[str] = None
    min_ocr_text_length: int = 120

    extract_tables: bool = True
    extract_figures: bool = True
    figure_min_width: float = 50.0
    figure_min_height: float = 50.0

    detect_columns: bool = True
    min_column_gap_pts: float = 30.0
    detect_headers_footers: bool = True
    margin_sample_pages: int = 15
    header_crop_ratio: float = 0.06
    footer_crop_ratio: float = 0.94

    preserve_coordinates: bool = True
    parallel_processing: bool = True
    max_workers: Optional[int] = None
    media_dir: str = os.path.join("data", "media")
    output_parsed_json: str = os.path.join("data", "parsed", "parsed_document.json")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enable_ocr": self.enable_ocr,
            "ocr_languages": self.ocr_languages,
            "extract_tables": self.extract_tables,
            "extract_figures": self.extract_figures,
            "detect_columns": self.detect_columns,
            "detect_headers_footers": self.detect_headers_footers,
            "parallel_processing": self.parallel_processing,
            "media_dir": self.media_dir,
            "output_parsed_json": self.output_parsed_json
        }
