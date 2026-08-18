"""
=============================================================================
  MODULAR PDF PARSER — Isolated OCR Extractor Service
=============================================================================
"""

from __future__ import annotations

import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger("OCRExtractor")


class OCRExtractor:
    """Isolated OCR Service managing Tesseract initialization once per process."""

    def __init__(self, languages: str = "eng+ara", custom_cmd: Optional[str] = None):
        self.languages = languages
        self.custom_cmd = custom_cmd
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Returns True if pytesseract, PIL, and Tesseract executable are verified."""
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
            self.ImageEnhance = __import__("PIL.ImageEnhance", fromlist=["ImageEnhance"])
        except ImportError:
            logger.warning("pytesseract or PIL is not installed. OCR disabled.")
            self._available = False
            return False

        if self.custom_cmd and os.path.exists(self.custom_cmd):
            self.pytesseract.pytesseract.tesseract_cmd = self.custom_cmd
            self._available = True
            return True

        if shutil.which("tesseract"):
            self._available = True
            return True

        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\FreeComp\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        for p in common_paths:
            if os.path.exists(p):
                self.pytesseract.pytesseract.tesseract_cmd = p
                self._available = True
                return True

        self._available = False
        return False

    def extract_region(self, page_obj: Any, bbox: tuple) -> str:
        """Performs OCR on a specific bounding box crop."""
        if not self.is_available():
            return ""

        try:
            cropped = page_obj.crop(bbox)
            pil_img = cropped.to_image(resolution=300).original
            img_gray = pil_img.convert("L")
            w, h = img_gray.size
            img_scaled = img_gray.resize((w * 2, h * 2), self.Image.Resampling.LANCZOS)
            enhancer = self.ImageEnhance.Contrast(img_scaled)
            img_contrast = enhancer.enhance(2.0)
            processed_img = img_contrast.point(lambda p: 255 if p > 128 else 0)

            text = self.pytesseract.image_to_string(processed_img, lang=self.languages)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR region extraction failed gracefully ({e}).")
            return ""
