# src/aee/config/__init__.py
"""Configuration module for AutoEvoExtractor."""

from aee.infrastructure.config.settings import settings
from aee.infrastructure.config.logging import setup_logging

__all__ = ["settings", "setup_logging"]