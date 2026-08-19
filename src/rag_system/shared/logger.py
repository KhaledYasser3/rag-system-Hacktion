"""
Centralized logging utility.
"""

import sys
import logging

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Configures and returns a standard system logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
