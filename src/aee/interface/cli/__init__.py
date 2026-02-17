"""CLI commands for AutoEvoExtractor.

This module provides command-line interfaces for all major operations.
"""

from .extract import extract_command
from .optimize import optimize_command
from .parse import parse_command

__all__ = [
    "extract_command",
    "optimize_command",
    "parse_command",
]
