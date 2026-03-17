# src/aee/infrastructure/config/__init__.py
"""Configuration module for AutoEvoExtractor."""

from aee.infrastructure.config.settings import Settings
from aee.infrastructure.config.logging import setup_logging
from aee.infrastructure.config.environments import (
    load_settings_for_environment,
    load_dev_settings,
    load_test_settings,
    load_prod_settings,
)
from aee.infrastructure.llm.provider import setup_teacher, setup_student

__all__ = [
    "Settings",
    "setup_logging",
    "load_settings_for_environment",
    "load_dev_settings",
    "load_test_settings",
    "load_prod_settings",
    "setup_teacher",
    "setup_student",
]
