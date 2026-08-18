"""
=============================================================================
  MODULAR PDF PARSER — Dynamic Margin & Header/Footer Detector
=============================================================================
  Identifies running headers/footers across sample pages and returns Y-crop bounds.
=============================================================================
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, Any, Set, List

logger = logging.getLogger("MarginDetector")


class MarginDetector:
    """Scans sample pages to detect repeating headers/footers and compute dynamic crop limits."""

    def __init__(self, num_samples: int = 15):
        self.num_samples = num_samples

    def detect_margins(self, backend_obj: Any) -> Dict[str, Any]:
        """Scans document to determine dynamic top/bottom crop bounds."""
        top_line_ys = []
        bottom_line_ys = []
        repeating_headers = Counter()
        repeating_footers = Counter()

        total = backend_obj.total_pages
        if total == 0:
            return {"header_limit": 50.0, "footer_limit": 790.0, "repeating_headers": set(), "repeating_footers": set()}

        step = max(1, total // self.num_samples)
        sample_indices = list(range(1, total + 1, step))[:self.num_samples]
        page_height = 842.0

        for page_num in sample_indices:
            try:
                page = backend_obj.get_page(page_num)
                page_height = page.height
                words = page.extract_words()

                lines = {}
                for w in words:
                    y_coord = round(w["top"], 1)
                    found = False
                    for k in lines.keys():
                        if abs(k - w["top"]) < 4:
                            lines[k].append(w)
                            found = True
                            break
                    if not found:
                        lines[w["top"]] = [w]

                height_15 = page_height * 0.15
                height_85 = page_height * 0.85

                for y, w_list in lines.items():
                    w_list = sorted(w_list, key=lambda x: x["x0"])
                    line_text = " ".join([w["text"] for w in w_list]).strip()
                    if len(line_text) < 5:
                        continue
                    if y < height_15:
                        repeating_headers[line_text] += 1
                        top_line_ys.append(y)
                    elif y > height_85:
                        repeating_footers[line_text] += 1
                        bottom_line_ys.append(y)
            except Exception as e:
                logger.warning(f"Margin detection failed on sample page {page_num}: {e}")

        threshold = max(2, int(len(sample_indices) * 0.3))
        actual_headers = {t for t, c in repeating_headers.items() if c >= threshold}
        actual_footers = {t for t, c in repeating_footers.items() if c >= threshold}

        header_crop_limit = page_height * 0.06
        footer_crop_limit = page_height * 0.94

        if actual_headers and top_line_ys:
            header_crop_limit = max(top_line_ys) + 8.0
        if actual_footers and bottom_line_ys:
            footer_crop_limit = min(bottom_line_ys) - 8.0

        return {
            "header_limit": header_crop_limit,
            "footer_limit": footer_crop_limit,
            "repeating_headers": actual_headers,
            "repeating_footers": actual_footers,
            "page_height": page_height
        }
