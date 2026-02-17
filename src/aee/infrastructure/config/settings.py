# src/aee/infrastructure/config/settings.py
"""Configuration settings for AutoEvoExtractor."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class ProjectConfig(BaseModel):
    """Project-level configuration settings."""
    name: str = "autoevoextractor"
    log_level: str = "INFO"


class PathsConfig(BaseModel):
    """File system paths configuration."""
    pdf_dir: Path = Path("data/pdf")
    parsed_dir: Path = Path("data/parsed")
    ground_truth_dir: Path = Path("data/ground_truth")
    splits_file: Path = Path("data/splits/nanozymes.json")
    agents_dir: Path = Path("data/agents")
    extractions_dir: Path = Path("data/extractions")
    logs_dir: Path = Path("logs")

    @field_validator("*", mode="before")
    @classmethod
    def cast_to_path(cls, v: Any) -> Path:
        """Cast input value to Path object."""
        return Path(v) if v else v


class OllamaConfig(BaseModel):
    """Ollama-specific configuration.

    Environment variables:
        OLLAMA_BASE_URL: Override the Ollama server URL (default: http://localhost:11434)
    """
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        description="Ollama server base URL"
    )
    num_ctx: int = 32000
    num_predict: int = 4096
    repeat_penalty: float = 1.2
    repeat_last_n: int = 64
    stream: bool = True


class NonOllamaConfig(BaseModel):
    """Non-Ollama LLM configuration."""
    api_key: Optional[SecretStr] = None
    max_tokens: int = 4096


class LLMInstanceConfig(BaseModel):
    """Configuration for a single LLM instance."""
    use_ollama: bool = True
    model: str = "mistral-small3.1-24b-128k:latest"
    timeout: int = 600
    max_retries: int = 3
    temperature: float = 0.0
    rate_limit_delay: float = 1.0
    top_p: float = 0.1
    repeat_penalty: float = 1.2
    repeat_last_n: int = 64
    enable_cache: bool = True  # Enable LLM response caching

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    non_ollama: NonOllamaConfig = Field(default_factory=NonOllamaConfig)


class LLMConfig(BaseModel):
    """Configuration for LLM instances."""
    student: LLMInstanceConfig = Field(default_factory=LLMInstanceConfig)
    teacher: LLMInstanceConfig = Field(default_factory=LLMInstanceConfig)


class DoclingConfig(BaseModel):
    """Docling parser configuration."""
    device: Literal["cpu", "cuda", "mps"] = "cpu"
    num_threads: int = 4
    do_ocr: bool = True
    do_table_structure: bool = True


class MarkerConfig(BaseModel):
    """Marker parser configuration."""
    device: Literal["cpu", "cuda"] = "cpu"


class IngestionConfig(BaseModel):
    """Document ingestion configuration."""
    parser: Literal["docling", "marker"] = "docling"
    overwrite: bool = False
    
    docling: DoclingConfig = Field(default_factory=DoclingConfig)
    marker: MarkerConfig = Field(default_factory=MarkerConfig)


class OptimizationConfig(BaseModel):
    """Optimization and training configuration."""
    total_load: int = 20
    train_split: int = 20
    num_candidates: int = 10
    num_trials: int = 50
    max_bootstrapped_demos: int = 2
    max_labeled_demos: int = 2
    minibatch: bool = False
    minibatch_size: int = 1
    view_data_batch_size: int = 3
    metric_threshold: float = 1.0
    init_temperature: float = 0.5
    random_seed: int = 42
    use_cache: bool = True
    verbose: bool = True


class EvaluationConfig(BaseModel):
    """Evaluation configuration."""
    float_tolerance: float = 0.05
    compare_fields: List[str] = Field(default_factory=list)


class TaskConfig(BaseModel):
    """Task-specific configuration."""
    name: str = "nanozymes"
    initial_instruction_file: str  # Required, no default - must be explicitly set
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    @field_validator("initial_instruction_file")
    @classmethod
    def validate_initial_instruction_file(cls, v: str) -> str:
        """Validate that initial_instruction_file is not empty."""
        if not v or not v.strip():
            raise ValueError("initial_instruction_file cannot be empty")
        return v


class ExtractionConfig(BaseModel):
    """Extraction configuration."""
    enable_cache: bool = False


class Settings(BaseSettings):
    """Main application settings with environment variable support."""
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    parsing: IngestionConfig = Field(default_factory=IngestionConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "Settings":
        """Load settings with the following priority:
        
        1. Default YAML (relative to this file)
        2. Custom YAML (if provided)
        3. Environment variables (handled by Pydantic)
        
        Args:
            config_path: Path to custom configuration YAML file.
            
        Returns:
            Settings: Loaded settings instance.
        """
        # Calculate base directory correctly (project root)
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        default_path = base_dir / "config" / "default.yaml"
        
        config_data = {}
        
        # Load default config if it exists
        if default_path.exists():
            try:
                with open(default_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded default configuration from {default_path}")
            except Exception as e:
                logger.warning(f"Failed to load default config from {default_path}: {e}")
                config_data = {}
        else:
            logger.warning(f"Default config not found at {default_path}. Using internal defaults.")

        # Load custom config if provided
        if config_path:
            custom_path = Path(config_path)
            # If path is not absolute, resolve it relative to config/ directory
            if not custom_path.is_absolute():
                custom_path = base_dir / "config" / custom_path
            if custom_path.exists():
                try:
                    with open(custom_path, "r", encoding="utf-8") as f:
                        custom_data = yaml.safe_load(f) or {}
                        cls._deep_update(config_data, custom_data)
                    logger.info(f"Loaded custom configuration from {custom_path}")
                except Exception as e:
                    logger.warning(f"Failed to load custom config from {custom_path}: {e}")
            else:
                logger.warning(f"Custom config {custom_path} not found. Using defaults.")

        # Set default task config if not present
        if "task" not in config_data:
            config_data["task"] = {
                "name": "nanozymes",
                "evaluation": {
                    "float_tolerance": 0.05,
                    "compare_fields": []
                }
            }

        # Resolve all paths relative to project root
        config_data = cls._resolve_paths(config_data, base_dir)

        return cls(**config_data)

    @classmethod
    def _resolve_paths(cls, config_data: dict, base_dir: Path) -> dict:
        """Resolve path values relative to project root.

        Recursively processes the config dictionary and converts values
        that look like file paths (strings containing '/' or ending with
        common file extensions) to absolute paths.

        Args:
            config_data: Configuration dictionary.
            base_dir: Project root directory.

        Returns:
            Configuration dictionary with resolved paths.
        """
        import re

        def is_path_like(value: str) -> bool:
            """Check if a string looks like a file path."""
            if not isinstance(value, str):
                return False
            # Skip empty strings
            if not value:
                return False
            # Skip URLs (http://, https://, ftp://, etc.)
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', value):
                return False
            # Check for path separators or file extensions
            return '/' in value or value.endswith(('.txt', '.yaml', '.yml', '.json', '.csv', '.md'))

        def resolve_value(value: Any) -> Any:
            """Resolve a single value if it's a path."""
            if is_path_like(value):
                path = Path(value)
                # Don't modify absolute paths
                if path.is_absolute():
                    return value
                # Resolve relative paths against project root
                resolved = base_dir / path
                return str(resolved)
            return value

        def process_dict(d: dict) -> dict:
            """Recursively process dictionary."""
            result = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    result[k] = process_dict(v)
                elif isinstance(v, list):
                    result[k] = [resolve_value(item) if isinstance(item, str) else item for item in v]
                elif isinstance(v, str):
                    result[k] = resolve_value(v)
                else:
                    result[k] = v
            return result

        return process_dict(config_data)

    @staticmethod
    def _deep_update(base_dict: dict, update_with: dict) -> None:
        """Recursively update a dictionary with another dictionary.
        
        Args:
            base_dict: The dictionary to update.
            update_with: The dictionary to update with.
        """
        for k, v in update_with.items():
            if isinstance(v, dict) and k in base_dict and isinstance(base_dict[k], dict):
                Settings._deep_update(base_dict[k], v)
            else:
                base_dict[k] = v


# Initialize settings
settings = Settings.load()