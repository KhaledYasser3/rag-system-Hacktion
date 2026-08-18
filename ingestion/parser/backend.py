"""
=============================================================================
  MODULAR PDF PARSER — PDF Backend Abstraction
=============================================================================
  Abstract interface for PDF library operations (pdfplumber, PyMuPDF, etc.)
  isolating PDF library calls from business logic.
=============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class PDFPageBackend(ABC):
    """Abstract interface for a single PDF page."""

    @property
    @abstractmethod
    def page_number(self) -> int: ...

    @property
    @abstractmethod
    def width(self) -> float: ...

    @property
    @abstractmethod
    def height(self) -> float: ...

    @abstractmethod
    def extract_text(self, bbox: Optional[Tuple[float, float, float, float]] = None) -> str: ...

    @abstractmethod
    def extract_words(self, keep_blank_chars: bool = False) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def extract_tables(self) -> List[Any]: ...

    @abstractmethod
    def get_images(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def crop(self, bbox: Tuple[float, float, float, float]) -> PDFPageBackend: ...


class PDFBackend(ABC):
    """Abstract interface for PDF document rendering and extraction."""

    @abstractmethod
    def open(self, pdf_path: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def total_pages(self) -> int: ...

    @abstractmethod
    def get_page(self, page_num: int) -> PDFPageBackend: ...

    @abstractmethod
    def get_outlines(self) -> List[Tuple[int, str, Any]]: ...


class PDFPlumberPageBackend(PDFPageBackend):
    """pdfplumber implementation of PDFPageBackend."""

    def __init__(self, page_obj: Any):
        self._page = page_obj

    @property
    def page_number(self) -> int:
        return self._page.page_number

    @property
    def width(self) -> float:
        return self._page.width

    @property
    def height(self) -> float:
        return self._page.height

    def extract_text(self, bbox: Optional[Tuple[float, float, float, float]] = None) -> str:
        target = self._page.crop(bbox) if bbox else self._page
        return target.extract_text() or ""

    def extract_words(self, keep_blank_chars: bool = False) -> List[Dict[str, Any]]:
        return self._page.extract_words(keep_blank_chars=keep_blank_chars, extra_attrs=["size", "fontname"]) or []

    def extract_tables(self) -> List[Any]:
        return self._page.find_tables() or []

    def get_images(self) -> List[Dict[str, Any]]:
        return getattr(self._page, "images", []) or []

    def crop(self, bbox: Tuple[float, float, float, float]) -> PDFPageBackend:
        clamped = (
            max(0.0, min(self.width - 1.0, bbox[0])),
            max(0.0, min(self.height - 1.0, bbox[1])),
            max(1.0, min(self.width, bbox[2])),
            max(1.0, min(self.height, bbox[3]))
        )
        return PDFPlumberPageBackend(self._page.crop(clamped))


class PDFPlumberBackend(PDFBackend):
    """pdfplumber implementation of PDFBackend."""

    def __init__(self):
        import pdfplumber
        self.pdfplumber = pdfplumber
        self._pdf = None

    def open(self, pdf_path: str) -> None:
        self._pdf = self.pdfplumber.open(pdf_path)

    def close(self) -> None:
        if self._pdf:
            self._pdf.close()
            self._pdf = None

    @property
    def total_pages(self) -> int:
        return len(self._pdf.pages) if self._pdf else 0

    def get_page(self, page_num: int) -> PDFPageBackend:
        return PDFPlumberPageBackend(self._pdf.pages[page_num - 1])

    def get_outlines(self) -> List[Tuple[int, str, Any]]:
        outlines = []
        if not self._pdf:
            return outlines
        try:
            raw_outlines = list(self._pdf.doc.get_outlines())
            for item in raw_outlines:
                level, title, dest = item[0], item[1], item[2]
                page_idx = None
                if isinstance(dest, int):
                    page_idx = dest + 1
                elif isinstance(dest, list) and len(dest) > 0 and isinstance(dest[0], int):
                    page_idx = dest[0] + 1
                if page_idx:
                    outlines.append((level, title, page_idx))
        except Exception:
            pass
        return outlines
