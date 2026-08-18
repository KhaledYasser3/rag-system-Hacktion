"""
=============================================================================
  MODULAR PDF PARSER — Reading Order Sorter (Recursive XY-Cut)
=============================================================================
"""

from __future__ import annotations

from typing import List, Dict, Any, Tuple


class ReadingOrderSorter:
    """Sorts page words into logical reading order using recursive projection profile splits."""

    def sort_words(
        self,
        words: List[Dict[str, Any]],
        bbox: Tuple[float, float, float, float],
        horizontal_threshold: float = 15.0,
        vertical_threshold: float = 25.0
    ) -> List[Dict[str, Any]]:
        """Recursively cuts bounding box into reading order elements."""
        x0, top, x1, bottom = bbox

        box_elements = [
            w for w in words
            if (w["x0"] >= x0 - 1 and w["x1"] <= x1 + 1 and
                w["top"] >= top - 1 and w["bottom"] <= bottom + 1)
        ]

        if not box_elements:
            return []

        # Analyze horizontal (Y-axis) projection
        y_bins = [0] * int(bottom - top + 2)
        for el in box_elements:
            y0_idx = int(max(0, el["top"] - top))
            y1_idx = int(min(len(y_bins) - 1, el["bottom"] - top))
            for y in range(y0_idx, y1_idx + 1):
                y_bins[y] += 1

        horizontal_gaps = []
        gap_start = None
        for y in range(len(y_bins)):
            if y_bins[y] == 0:
                if gap_start is None:
                    gap_start = y
            else:
                if gap_start is not None:
                    gap_w = y - gap_start
                    if gap_w >= horizontal_threshold:
                        horizontal_gaps.append((gap_start + top, y + top))
                    gap_start = None

        if horizontal_gaps:
            largest_gap = max(horizontal_gaps, key=lambda g: g[1] - g[0])
            split_y = largest_gap[0] + (largest_gap[1] - largest_gap[0]) / 2

            top_box = (x0, top, x1, split_y)
            bottom_box = (x0, split_y, x1, bottom)

            return (self.sort_words(box_elements, top_box, horizontal_threshold, vertical_threshold) +
                    self.sort_words(box_elements, bottom_box, horizontal_threshold, vertical_threshold))

        # Analyze vertical (X-axis) projection
        x_bins = [0] * int(x1 - x0 + 2)
        for el in box_elements:
            x0_idx = int(max(0, el["x0"] - x0))
            x1_idx = int(min(len(x_bins) - 1, el["x1"] - x0))
            for x in range(x0_idx, x1_idx + 1):
                x_bins[x] += 1

        vertical_gaps = []
        gap_start = None
        for x in range(len(x_bins)):
            if x_bins[x] == 0:
                if gap_start is None:
                    gap_start = x
            else:
                if gap_start is not None:
                    gap_w = x - gap_start
                    if gap_w >= vertical_threshold:
                        vertical_gaps.append((gap_start + x0, x + x0))
                    gap_start = None

        if vertical_gaps:
            largest_gap = max(vertical_gaps, key=lambda g: g[1] - g[0])
            split_x = largest_gap[0] + (largest_gap[1] - largest_gap[0]) / 2

            left_box = (x0, top, split_x, bottom)
            right_box = (split_x, top, x1, bottom)

            return (self.sort_words(box_elements, left_box, horizontal_threshold, vertical_threshold) +
                    self.sort_words(box_elements, right_box, horizontal_threshold, vertical_threshold))

        return sorted(box_elements, key=lambda e: (round(e["top"], 1), e["x0"]))
