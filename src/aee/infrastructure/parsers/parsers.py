# src/aee/ingestion/parsers.py
"""Document parsers for AutoEvoExtractor."""

import logging
from pathlib import Path
from typing import Any, Union

# Marker
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

# Project
from aee.infrastructure.parsers.base import BaseParser
from aee.infrastructure.config.settings import MarkerConfig

logger = logging.getLogger(__name__)


class MarkerParser(BaseParser):
    """Parser using Marker library."""

    def __init__(self, config: MarkerConfig):
        """Initialize the Marker parser.

        Args:
            config: Configuration for the parser. Required.

        Raises:
            ValueError: If config is None.
        """
        if config is None:
            raise ValueError("Configuration object is required for MarkerParser")
        self.cfg = config
        logger.info(f"Initializing Marker on {self.cfg.device}...")
        self.converter = PdfConverter(
            artifact_dict=create_model_dict(device=self.cfg.device)
        )

    def parse(self, file_path: Union[str, Path]) -> str:
        """Parse a PDF file using Marker.

        Args:
            file_path: Path to the PDF file.

        Returns:
            str: Markdown text content.

        Raises:
            Exception: If parsing fails.
        """
        path = Path(file_path)
        logger.info(f"Marker processing: {path.name}")

        try:
            rendered = self.converter(str(path))

            # Extract text content with fallback chain
            text = (
                getattr(rendered, "markdown", None) or
                getattr(rendered, "text", None) or
                str(rendered)
            )

            return text

        except Exception as e:
            logger.error(f"Marker parsing failed for {path.name}: {str(e)}")
            raise


def get_parser(parser_name: str, config: Any = None) -> BaseParser:
    """Factory function to get a parser instance by name.

    Args:
        parser_name: Name of the parser ("marker").
        config: Configuration for the parser (MarkerConfig).

    Returns:
        Parser instance.

    Raises:
        ValueError: If parser_name is not recognized.
    """
    from aee.infrastructure.config.settings import MarkerConfig

    parser_name = parser_name.lower()

    if parser_name == "marker":
        if config is None or not isinstance(config, MarkerConfig):
            raise ValueError(
                f"MarkerParser requires MarkerConfig, got {type(config).__name__}"
            )
        return MarkerParser(config)
    else:
        raise ValueError(
            f"Unknown parser: {parser_name}. "
            f"Available parsers: 'marker'"
        )
