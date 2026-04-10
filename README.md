# AutoEvoExtractor

**A scientific data extraction system using Large Language Models with automatic prompt optimization.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-MIPROv2-green.svg)](https://github.com/stanfordnlp/dspy)

AutoEvoExtractor automatically extracts structured experimental data from scientific PDF documents using LLMs with automatic prompt optimization via DSPy's MIPROv2 algorithm.

## Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](docs/cli_reference.md) | Complete command reference |
| [Data Artifacts](docs/data_artifacts.md) | Data structure and file formats |
| [Configuration](docs/configuration.md) | YAML and environment variables |
| [Adding Tasks](docs/adding_tasks.md) | Creating new tasks (YAML) |
| [Architecture](docs/architecture.md) | System design |

---

## Requirements

- **Python:** 3.12+
- **LLM providers:** Ollama, HuggingFace Transformers (local), or API (OpenRouter, OpenAI, Anthropic, Gemini)
- **PDF parser:** Gemini API (primary) or Marker (local, GPU, optional)
- **GPU server:** NVIDIA GPU with CUDA 12.x support (A6000 recommended)

## Installation

### Option 1: Conda (local development with Jupyter)

```bash
conda env create -f environment.yml
conda activate aee
```

This installs all dependencies including Jupyter notebooks. The `environment.yml` uses `pyproject.toml` as the single source of truth for Python packages.

### Option 2: pip venv (GPU server, A6000)

```bash
python3.12 -m venv /opt/aee/env
source /opt/aee/env/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -e ".[dev]"           # dev tools
pip install -e ".[dev,quant]"     # + quantization (4bit/8bit)
```

> **Note:** Do not install `[notebook]` extras on the server.

### Optional dependency groups

| Group | Purpose | Install command |
|-------|---------|-----------------|
| `dev` | Testing, linting, type checking | `-e ".[dev]"` |
| `quant` | Model quantization (4bit/8bit) | `-e ".[dev,quant]"` |
| `notebook` | Jupyter, matplotlib, seaborn | `-e ".[dev,notebook]"` |
| `marker` | Marker PDF parser (GPU, requires `transformers<5.0`) | See note below |

> **Marker parser:** Requires `transformers<5.0` and is incompatible with the main dependency tree. If you need Marker, install it in a separate environment with pinned transformers version.

## Quick Start

```bash
# 1. Copy and configure environment variables
cp .env.example .env

# 2. Parse a PDF to Markdown (using Gemini)
aee-parse --file paper.pdf --config config/systems/example.yaml

# 3. Run extraction with a local LLM
aee-extract --config config/systems/example.yaml --task nanozymes

# 4. Optimize the agent
aee-optimize --config config/systems/example.yaml --task nanozymes
```

## Project Structure

```
├── src/aee/                  # Package source
│   ├── domain/               # Entities, tasks, evaluation
│   ├── application/          # Use cases, services
│   ├── infrastructure/       # LLM providers, parsers, storage
│   ├── interface/            # CLI
│   └── shared/               # Shared utilities
├── config/                   # YAML configurations
│   ├── systems/              # System configs (models, providers)
│   └── tasks/                # Task definitions
├── scripts/                  # Utility scripts
├── tests/                    # Unit and integration tests
├── pyproject.toml            # Package definition and dependencies
├── environment.yml           # Conda environment (local dev)
└── constraints.txt           # NCCL conflict resolution (conda only)
```
