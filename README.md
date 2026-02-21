# AutoEvoExtractor

**A scientific data extraction system using Large Language Models with automatic prompt optimization.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-MIPROv2-green.svg)](https://github.com/stanfordnlp/dspy)

AutoEvoExtractor automatically extracts structured experimental data from scientific PDF documents using LLMs with automatic prompt optimization via DSPy's MIPROv2 algorithm.

---

## Quick Start

### Installation

```bash
git clone https://github.com/ai-chem/AutoEvoExtractor.git
cd autoevoextractor

conda env create -f environment.yml
conda activate aee
pip install -e .
```

### LLM Setup

**Ollama (local):**
```bash
export OLLAMA_STUDENT_BASE_URL="http://localhost:11434"
export OLLAMA_TEACHER_BASE_URL="http://localhost:11434"

ollama pull mistral-small3.1-24b-128k:latest
ollama pull gpt-oss:120b
```

**OpenAI/Anthropic API:**
```bash
export LLM__STUDENT__USE_OLLAMA=false
export LLM__STUDENT__MODEL="gpt-4"
export OPENAI_API_KEY="sk-..."
```

### Workflow

#### 1. Data Preparation

```bash
# PDF files
mkdir -p data/pdf
cp /path/to/papers/*.pdf data/pdf/

# Ground truth (CSV)
# data/ground_truth/nanozymes.csv
filename,formula,activity,length,km_value
paper1.pdf,Fe3O4,peroxidase,10,0.05
paper2.pdf,CuO,oxidase,20,0.08

# Data splits (JSON)
# data/splits/nanozymes.json
{
  "train": ["paper1", "paper2"],
  "val": ["paper3"]
}
```

#### 2. Run Pipeline

```bash
# Parse PDFs
python scripts/parse.py --config default.yaml

# Optimize agent
python scripts/optimize.py --config default.yaml

# Extract data
python scripts/extract.py --config default.yaml --agent data/agents/nanozymes_latest.json
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](docs/cli_reference.md) | Complete command reference |
| [Data Artifacts](docs/data_artifacts.md) | Data structure and file formats |
| [Configuration](docs/configuration.md) | YAML and environment variables |
| [Adding Tasks](docs/adding_tasks.md) | Creating new tasks (YAML) |
| [Architecture](docs/architecture.md) | System design |

---

## Project Structure

```
autoevoextractor/
├── src/aee/
│   ├── domain/
│   │   ├── tasks/              # Task config, dynamic models, registry
│   │   ├── agents/             # Base agent abstract class
│   │   ├── entities/           # Domain entities (Document, Experiment, Extraction)
│   │   └── evaluation/         # Evaluation metrics (matcher, metrics)
│   ├── application/
│   │   ├── services/           # Application services (AgentManager, DatasetBuilder)
│   │   └── use_cases/          # Use cases (optimize_agent, parse_documents, predict_batch)
│   ├── infrastructure/
│   │   ├── agents/             # Agent implementations (UniversalExtractor)
│   │   ├── cache/              # LLM caching
│   │   ├── config/             # Settings, environments, logging
│   │   ├── llm/                # LLM providers (Ollama, OpenAI)
│   │   ├── parsers/            # Document parsers (Docling, Marker)
│   │   └── storage/            # Storage functions (agents, ground truth, splits, extractions)
│   ├── interface/
│   │   └── cli/                # CLI commands (parse, optimize, extract)
│   └── shared/                 # Exceptions, utilities
├── scripts/                    # Entry points
│   ├── parse.py                # Parse PDFs
│   ├── optimize.py             # Optimize agent
│   ├── extract.py              # Extract data
│   ├── generate_manual_agent.py # Generate manual agent
│   └── patch_dspy_mipro_threshold.py # DSPy bug fix
├── config/
│   ├── default.yaml            # Default configuration
│   ├── dev.yaml                # Development configuration
│   └── initial_instructions/   # Task instruction templates
├── data/
│   ├── pdf/                    # Source PDFs
│   ├── parsed/                 # Parsed JSON
│   ├── ground_truth/           # Training CSV
│   ├── splits/                 # Data splits JSON
│   ├── agents/                 # Trained agents
│   └── extractions/            # Extraction results
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── notebooks/                  # Jupyter notebooks
└── docs/                       # Documentation
```

---

## Adding New Tasks

### YAML Approach (Recommended)

```bash
mkdir -p src/aee/domain/tasks/mytask
```

Create `src/aee/domain/tasks/mytask/task.yaml`:

```yaml
name: mytask
description: Extract my domain experiments

fields:
  field_name:
    type: str
    description: "Field description"
    required: true

compare_fields:
  - field_name
float_tolerance: 0.05

instruction_file: config/initial_instructions/mytask.txt
```

**Time:** 15-30 minutes for simple tasks

[Full guide →](docs/adding_tasks.md)

---

## Configuration

### Settings Priority

1. **Environment variables** (`.env`, `AEE__*`)
2. **CLI arguments** (`--config` — только путь к файлу конфигурации)
3. **YAML files** (`config/default.yaml`)
4. **Internal defaults**

> **Note:** CLI аргументы не переопределяют настройки напрямую, а передают путь к конфигурационному файлу.

### Key Settings

```yaml
# LLM
llm:
  student:
    use_ollama: true
    model: "mistral-small3.1-24b-128k:latest"
    enable_cache: true

# Optimization
optimization:
  num_trials: 70
  use_cache: true

# Paths
paths:
  pdf_dir: "data/pdf"
  ground_truth_dir: "data/ground_truth"
  splits_file: "data/splits/nanozymes.json"

# Task (nested structure)
task:
  name: "nanozymes"
  initial_instruction_file: "config/initial_instructions/nanozymes_sota.txt"
  evaluation:
    compare_fields:
      - formula
      - activity
    float_tolerance: 0.05
```

### Environment Variables

```bash
# LLM Provider
export LLM__STUDENT__USE_OLLAMA=false
export OPENAI_API_KEY="sk-..."

# Paths
export PATHS__PDF_DIR="data/my_pdfs"

# Optimization
export OPTIMIZATION__NUM_TRIALS="50"

# Logging
export LOG_LEVEL="DEBUG"
```

---

## Testing

```bash
# All tests
pytest

# Unit tests with coverage
pytest tests/unit -v --cov=src/aee

# Integration tests (excluding slow)
pytest tests/integration -v -m "not slow"

# Specific file
pytest tests/unit/domain/test_task_loader.py -v
```

**Test Structure:**
- `tests/unit/` — Unit tests for individual components
- `tests/integration/` — Integration tests for component interaction
- `tests/e2e/` — End-to-end workflow tests

---

## Requirements

- **Python:** 3.11+
- **LLM:** Ollama (local) or OpenAI/Anthropic API
- **Core dependencies:** dspy-ai, pydantic, pandas, mlflow, docling

[Full list →](pyproject.toml)

---

## Architecture

**Key Components:**

| Component | Purpose |
|-----------|---------|
| **Task Config** | YAML task configuration (single source of truth) |
| **Dynamic Models** | Pydantic models generated from config |
| **Dynamic Signature** | DSPy signatures generated from config |
| **Task Registry** | Task registry with component caching |

**New Architecture (after refactoring):**

```
┌─────────────────────────────────────┐
│ INTERFACE (CLI)                     │
│ - parse.py, optimize.py, extract.py │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ APPLICATION (Use Cases)             │
│ - optimize_agent(), extract_batch() │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ DOMAIN (Task Config + Dynamic)      │
│ - TaskConfig, *.yaml manifests      │
│ - create_experiment_model(config)   │
│ - create_signature(config, model)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ INFRASTRUCTURE (Functions)          │
│ - save_agent(), load_agent()        │
│ - load_ground_truth(), load_splits()│
└─────────────────────────────────────┘
```

---

## License

MIT
