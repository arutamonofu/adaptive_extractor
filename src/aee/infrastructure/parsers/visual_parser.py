# src/aee/infrastructure/parsers/visual_parser.py
"""Visual-anchored document parser using Gemini and the aee_visual pipeline."""

import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Union

from aee.infrastructure.config.settings import AEEVisualParserConfig
from aee.infrastructure.parsers.base import BaseParser
from aee.infrastructure.parsers.parsers import GeminiParser

logger = logging.getLogger(__name__)


class AEEVisualParser(BaseParser):
    """Parser that first extracts markdown text using GeminiParser (with visual anchors),
    then runs the aee_visual pipeline to extract visual charts and tables and insert them.
    """

    def __init__(self, config: AEEVisualParserConfig):
        """Initialize the AEEVisualParser.

        Args:
            config: Configuration settings for the visual parser.
        """
        if config is None:
            raise ValueError("AEEVisualParserConfig is required")

        self.cfg = config
        # Initialize the base parser using the nested Gemini configuration
        self.base_parser = GeminiParser(config.gemini)
        logger.info("Initialized AEEVisualParser with nested Gemini parser configuration")

    def parse(self, file_path: Union[str, Path]) -> str:
        """Parse a PDF file into Markdown text with embedded charts/tables.

        Args:
            file_path: Path to the input PDF file.

        Returns:
            str: Enriched Markdown text containing inserted tables/charts.
        """
        pdf_path = Path(file_path).resolve()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"[AEEVisualParser] Starting parsing pipeline for: {pdf_path.name}")

        # Stage 1: Base text extraction with GeminiParser
        logger.info("[AEEVisualParser] Step 1/6: Running base text parser with Gemini to extract anchors...")
        initial_md = self.base_parser.parse(pdf_path)
        if not initial_md:
            logger.warning("[AEEVisualParser] Gemini parser returned empty markdown content")
            return ""

        logger.info(
            f"[AEEVisualParser] Step 2/6: Text parsing completed (Markdown size: {len(initial_md)} characters)"
        )

        # Use temporary directory for the pipeline's inputs and outputs
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir).resolve()
            temp_md_path = temp_dir_path / "article_anchors.md"
            temp_out_dir = temp_dir_path / "aee_visual_run"

            # Stage 2: Save initial markdown to a temp file
            logger.info(f"[AEEVisualParser] Step 3/6: Writing initial markdown with anchors to: {temp_md_path}")
            temp_md_path.write_text(initial_md, encoding="utf-8")
            temp_out_dir.mkdir(parents=True, exist_ok=True)

            # Locate run.py inside aee_visual directory
            pipeline_config = Path(self.cfg.pipeline_config_path).resolve()
            aee_visual_root = pipeline_config.parent.parent
            run_py_path = aee_visual_root / "run.py"

            if not run_py_path.exists():
                # Fallback to default path specified in instructions if resolved path is invalid
                fallback_path = Path("/home/arutamonofu/dev/fast/aee_visual/run.py")
                if fallback_path.exists():
                    logger.debug(f"[AEEVisualParser] Root run.py not found at {run_py_path}, using fallback: {fallback_path}")
                    run_py_path = fallback_path
                else:
                    raise FileNotFoundError(
                        f"Could not locate aee_visual run.py. Checked {run_py_path} and fallback {fallback_path}"
                    )

            # Stage 3: Run the aee_visual pipeline
            logger.info(f"[AEEVisualParser] Step 4/6: Executing aee_visual pipeline from {run_py_path}...")
            cmd = [
                sys.executable,
                str(run_py_path),
                "pipeline",
                "--config", str(self.cfg.pipeline_config_path),
                "--pdf", str(pdf_path),
                "--markdown", str(temp_md_path),
                "--task-config", str(self.cfg.task_config_path),
                "--out-dir", str(temp_out_dir),
                "--force"
            ]

            logger.info(f"[AEEVisualParser] Running command: {' '.join(cmd)}")
            
            # Execute and pipe output to logging
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                with process:
                    if process.stdout:
                        for line in process.stdout:
                            logger.info(f"[aee_visual] {line.rstrip()}")

                return_code = process.wait()
                if return_code != 0:
                    raise subprocess.CalledProcessError(return_code, cmd)

                logger.info("[AEEVisualParser] Step 5/6: aee_visual pipeline finished successfully")

            except Exception as e:
                logger.error(f"[AEEVisualParser] Error running aee_visual pipeline: {e}")
                raise

            # Stage 4: Read the enriched markdown output
            # By default insert_visual_tables outputs to <out_dir>/service/table_insertion/article.with_visual_tables.md
            output_md_path = temp_out_dir / "service" / "table_insertion" / "article.with_visual_tables.md"
            if not output_md_path.exists():
                logger.warning(
                    f"[AEEVisualParser] Output markdown not found at default location: {output_md_path}. "
                    "Searching recursively for any markdown file..."
                )
                md_files = list(temp_out_dir.glob("**/*.md"))
                if md_files:
                    # Prefer files with "with_visual_tables" in name
                    with_tables = [f for f in md_files if "with_visual_tables" in f.name]
                    output_md_path = with_tables[0] if with_tables else md_files[0]
                    logger.info(f"[AEEVisualParser] Found alternative output markdown at: {output_md_path}")
                else:
                    raise FileNotFoundError(
                        f"aee_visual pipeline completed but no output markdown was found in {temp_out_dir}"
                    )

            logger.info(f"[AEEVisualParser] Reading enriched markdown from: {output_md_path}")
            enriched_md = output_md_path.read_text(encoding="utf-8")

            logger.info("[AEEVisualParser] Step 6/6: Cleaned up temporary directory")
            return enriched_md
