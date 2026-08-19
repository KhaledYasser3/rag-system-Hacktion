"""
Text cleaning and normalization module for PDF parsed text elements.
"""

import re

def clean_text(text: str) -> str:
    """
    Cleans raw text by normalizing whitespace, hyphenated words, and non-printable characters.
    """
    if not text:
        return ""
    # Resolve intra-page hyphenation
    cleaned = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    # Normalize whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)
    return cleaned.strip()
