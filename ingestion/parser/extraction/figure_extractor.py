"""
=============================================================================
  MODULAR PDF PARSER — Figure & Media Extractor
=============================================================================
"""

from __future__ import annotations

import os
import re
import logging
from typing import List, Dict, Any, Tuple
from ingestion.parser.models import ContentBlock, BlockType

logger = logging.getLogger("FigureExtractor")


class FigureExtractor:
    """Extracts figures, diagrams, and image bounding boxes from PDF pages."""

    def __init__(self, media_dir: str = os.path.join("data", "media"), min_width: float = 50.0, min_height: float = 50.0):
        self.media_dir = media_dir
        self.min_width = min_width
        self.min_height = min_height
        os.makedirs(self.media_dir, exist_ok=True)

    def extract_page_figures(self, page_obj: Any, page_num: int) -> List[ContentBlock]:
        """Extracts image crops exceeding minimum dimensions and returns ContentBlock objects."""
        blocks: List[ContentBlock] = []
        raw_images = page_obj.get_images()

        for idx, im in enumerate(raw_images):
            w = im.get("width", 0)
            h = im.get("height", 0)
            if w >= self.min_width and h >= self.min_height:
                try:
                    raw_box = (im["x0"], im["top"], im["x1"], im["bottom"])
                    fig_filename = f"figure_page_{page_num}_{idx+1}.png"
                    fig_path = os.path.join(self.media_dir, fig_filename)

                    # Crop image to disk
                    cropped = page_obj.crop(raw_box)
                    try:
                        cropped._page.to_image(resolution=150).save(fig_path)
                    except Exception:
                        pass

                    caption = f"Figure extracted from Page {page_num}, Area {idx+1}"
                    fig_number = f"Figure {idx+1}"
                    fig_content = f"\n![{caption}]({fig_path})\n*Caption*: *{caption}*\n"

                    blocks.append(ContentBlock(
                        block_id=f"fig_p{page_num}_{idx+1}",
                        page_number=page_num,
                        block_type=BlockType.FIGURE,
                        title=fig_number,
                        content=fig_content,
                        bbox=raw_box,
                        metadata={
                            "figure_number": fig_number,
                            "caption": caption,
                            "image_path": fig_path,
                            "width": w,
                            "height": h
                        }
                    ))
                except Exception as e:
                    logger.warning(f"Failed to extract figure {idx+1} on page {page_num}: {e}")

        return blocks
