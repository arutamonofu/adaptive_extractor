"""Unit tests for the AEEVisualParser composite parser."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aee.infrastructure.config.settings import (
    AEEVisualParserConfig,
    GeminiParserConfig,
    IngestionConfig,
)
from aee.infrastructure.parsers import AEEVisualParser, get_parser


@pytest.mark.unit
class TestAEEVisualParserConfig:
    """Tests for AEEVisualParserConfig."""

    def test_create_config(self):
        """Test creating config with required paths and nested Gemini config."""
        config = AEEVisualParserConfig(
            task_config_path="configs/schema_nanozymes.yaml",
            pipeline_config_path="configs/pipeline.yaml",
            gemini=GeminiParserConfig(model_name="gemini-2.0-flash")
        )

        assert config.task_config_path == "configs/schema_nanozymes.yaml"
        assert config.pipeline_config_path == "configs/pipeline.yaml"
        assert config.gemini.model_name == "gemini-2.0-flash"


@pytest.mark.unit
class TestIngestionConfigWithVisual:
    """Tests for IngestionConfig with AEEVisualParserConfig."""

    def test_ingestion_config_gemini_visual_requires_config(self):
        """Test IngestionConfig validation fails if gemini_visual is missing when selected."""
        with pytest.raises(ValueError, match="gemini_visual configuration is required"):
            IngestionConfig(
                parser="gemini_visual",
                overwrite=False,
            )

    def test_ingestion_config_gemini_visual_valid(self):
        """Test IngestionConfig validation succeeds with valid gemini_visual config."""
        config = IngestionConfig(
            parser="gemini_visual",
            overwrite=False,
            gemini_visual=AEEVisualParserConfig(
                task_config_path="configs/schema_nanozymes.yaml",
                pipeline_config_path="configs/pipeline.yaml"
            )
        )

        assert config.parser == "gemini_visual"
        assert config.gemini_visual.task_config_path == "configs/schema_nanozymes.yaml"


@pytest.mark.unit
class TestAEEVisualParser:
    """Tests for AEEVisualParser functionality."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_parser_initialization(self, mock_client):
        """Test initializing AEEVisualParser correctly passes config."""
        config = AEEVisualParserConfig(
            task_config_path="configs/schema_nanozymes.yaml",
            pipeline_config_path="configs/pipeline.yaml"
        )
        parser = AEEVisualParser(config)

        assert parser.cfg == config
        assert parser.base_parser is not None
        assert parser.base_parser.cfg == config.gemini

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch("google.genai.Client")
    @patch("subprocess.Popen")
    def test_parse_success(self, mock_popen, mock_client):
        """Test parse method runs the full text extraction and pipeline subprocess."""
        # 1. Setup mock inputs
        config = AEEVisualParserConfig(
            task_config_path="configs/schema_nanozymes.yaml",
            pipeline_config_path="configs/pipeline.yaml"
        )
        parser = AEEVisualParser(config)

        # Mock the base text parser behavior
        parser.base_parser.parse = MagicMock(return_value="Initial Markdown with <!-- AEE_VISUAL_ANCHOR: main_fig_1 -->")

        # Mock subprocess.Popen to write the output file dynamically
        def mock_popen_func(cmd, *args, **kwargs):
            out_dir_idx = cmd.index("--out-dir")
            out_dir_path = Path(cmd[out_dir_idx + 1])
            output_file = out_dir_path / "service" / "table_insertion" / "article.with_visual_tables.md"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("Enriched Markdown Content with Table", encoding="utf-8")

            proc = MagicMock()
            proc.stdout = ["Manifest stage complete", "Extraction stage complete"]
            proc.wait.return_value = 0
            proc.returncode = 0
            proc.__enter__.return_value = proc
            proc.__exit__.return_value = None
            return proc

        mock_popen.side_effect = mock_popen_func

        # 2. Execute parse
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "article.pdf"
            pdf_path.write_text("dummy pdf contents", encoding="utf-8")

            # Mock check for run.py existence to succeed
            with patch.object(Path, "exists", return_value=True):
                result = parser.parse(pdf_path)

        # 3. Assertions
        assert result == "Enriched Markdown Content with Table"
        parser.base_parser.parse.assert_called_once_with(pdf_path.resolve())
        mock_popen.assert_called_once()


@pytest.mark.unit
class TestParserFactoryWithVisual:
    """Tests that the parser factory supports the new parser."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch("google.genai.Client")
    def test_get_parser_factory(self, mock_client):
        """Test that get_parser correctly instantiates AEEVisualParser."""
        config = AEEVisualParserConfig(
            task_config_path="configs/schema_nanozymes.yaml",
            pipeline_config_path="configs/pipeline.yaml"
        )
        parser = get_parser("gemini_visual", config)

        assert isinstance(parser, AEEVisualParser)
        assert parser.cfg == config
