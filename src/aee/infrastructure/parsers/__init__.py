"""Document parsers for AutoEvoExtractor.

This module provides parsers for extracting text and tables from PDF
documents using the Marker parsing backend.
"""

from .base import BaseParser
from .parsers import MarkerParser, get_parser

# Alias for backward compatibility
DocumentParser = BaseParser

__all__ = [
    "BaseParser",
    "DocumentParser",
    "MarkerParser",
    "get_parser",
]
