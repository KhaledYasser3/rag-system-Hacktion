"""
=============================================================================
  MODULAR PDF PARSER — Column Detector
=============================================================================
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Any


class ColumnDetector:
    """Analyzes page character distribution to detect two-column layouts."""

    def __init__(self, min_gap_pts: float = 30.0):
        self.min_gap_pts = min_gap_pts

    def detect_columns(self, page_obj: Any) -> Optional[List[Tuple[float, float, float, float]]]:
        """Returns list of column crop boxes [(x0, top, x1, bottom)] if 2-column layout detected."""
        try:
            words = page_obj.extract_words()
            if not words:
                return None

            width = page_obj.width
            height = page_obj.height

            bins = [0] * int(width + 1)
            for w in words:
                x0 = int(max(0, w["x0"]))
                x1 = int(min(width, w["x1"]))
                for x in range(x0, x1 + 1):
                    if x < len(bins):
                        bins[x] += 1

            start_mid = int(width * 0.3)
            end_mid = int(width * 0.7)

            current_gap_start = None
            max_gap_start = None
            max_gap_width = 0

            for x in range(start_mid, end_mid):
                if bins[x] <= 1:
                    if current_gap_start is None:
                        current_gap_start = x
                else:
                    if current_gap_start is not None:
                        gap_w = x - current_gap_start
                        if gap_w > max_gap_width:
                            max_gap_width = gap_w
                            max_gap_start = current_gap_start
                        current_gap_start = None

            if current_gap_start is not None:
                gap_w = end_mid - current_gap_start
                if gap_w > max_gap_width:
                    max_gap_width = gap_w
                    max_gap_start = current_gap_start

            if max_gap_width >= self.min_gap_pts and max_gap_start is not None:
                mid_point = max_gap_start + (max_gap_width // 2)
                return [
                    (0.0, 0.0, float(mid_point), height),
                    (float(mid_point), 0.0, width, height)
                ]
        except Exception:
            pass

        return None
