# Configuration Reference

Complete reference for AutoEvoExtractor configuration.

## Configuration Priority

Settings loaded in order (highest to lowest priority):

1. **Environment variables** (`.env`, `AEE__*` overrides)
2. **CLI arguments** (`--config`, `--overwrite`, etc.)
3. **YAML files** (`config/default.yaml`, `config/<env>.yaml`)
4. **Internal defaults**

> ⚠️ **API keys** must be set via environment variables only — never in YAML files.

---

## YAML Configuration

### Complete Example

```yaml
# config/default.yaml

llm:
  student:
    use_ollama: true
    model: "mistral-small3.1-24b-128k:latest"
    temperature: 0.0
    timeout: 600
    enable_cache: true

optimization:
  num_trials: 70
  num_candidates: 10
  max_bootstrapped_demos: 1
  max_labeled_demos: 1
  use_cache: true

paths:
  pdf_dir: "data/pdf"
  parsed_dir: "data/parsed"
  ground_truth_dir: "data/ground_truth"
  splits_file: "data/splits/nanozymes.json"
  agents_dir: "data/agents"
  extractions_dir: "data/extractions"

task:
  name: "nanozymes"
  compare_fields:
    - formula
    - activity
    - length
  float_tolerance: 0.05
```

---

## Configuration Sections

### LLM Configuration

```yaml
llm:
  student:
    use_ollama: true              # Use Ollama (true) or API (false)
    model: "mistral-small3.1-24b-128k:latest"
    temperature: 0.0              # 0.0 for deterministic output
    timeout: 600                  # Request timeout (seconds)
    max_retries: 5                # Maximum retry attempts
    rate_limit_delay: 10.0        # Delay between API calls (seconds)
    top_p: 0.1                    # Nucleus sampling top-p parameter
    repeat_penalty: 1.2           # Penalty for repeated tokens
    repeat_last_n: 2048           # Tokens to consider for repeat penalty
    enable_cache: true            # Cache LLM responses
    
    # Ollama-specific settings
    ollama:
      ollama_base_url: "http://localhost:11434"
      num_ctx: 64000              # Context window size
      num_predict: 2048           # Max tokens to generate
      stream: false
    
    # Non-Ollama settings
    non_ollama:
      max_tokens: 4096            # Max tokens for API providers
```

### Optimization Configuration

```yaml
optimization:
  num_trials: 70                  # Number of MIPROv2 trials
  num_candidates: 10              # Candidates per trial
  max_bootstrapped_demos: 1       # Max bootstrapped examples
  max_labeled_demos: 1            # Max labeled examples
  use_cache: true                 # Cache during optimization
```

### Paths Configuration

```yaml
paths:
  pdf_dir: "data/pdf"                         # Input PDFs
  parsed_dir: "data/parsed"                   # Parsed JSON output
  ground_truth_dir: "data/ground_truth"       # Training CSV
  splits_file: "data/splits/nanozymes.json"   # Data splits (REQUIRED)
  agents_dir: "data/agents"                   # Trained agents
  extractions_dir: "data/extractions"         # Extraction results
```

### Task Configuration

Task configuration in `config/default.yaml` uses a nested structure under `task.evaluation.*`:

```yaml
# config/default.yaml
task:
  name: "nanozymes"
  initial_instruction_file: "config/initial_instructions/nanozymes_sota.txt"
  evaluation:
    compare_fields:            # Fields for evaluation
      - formula
      - activity
      - syngony
      - surface
      - length
      - width
      - depth
      - reaction_type
      - km_value
      - km_unit
      - vmax_value
      - vmax_unit
      - ph
      - temperature
      - c_min
      - c_max
      - c_const
      - c_const_unit
      - ccat_value
      - ccat_unit
    float_tolerance: 0.05      # 5% tolerance for floats
```

> **Note:** For backward compatibility, the legacy flat structure (`task.compare_fields`, `task.float_tolerance` at top level) is automatically converted to the nested format.

**Fields:**
- `name` — Task identifier (must match task name in `src/aee/domain/tasks/{task_name}/task.yaml`)
- `initial_instruction_file` — Path to initial instruction file for DSPy
- `evaluation.compare_fields` — List of field names used for evaluation during optimization
- `evaluation.float_tolerance` — Tolerance for floating-point comparisons (0.0 to 1.0)

---

## Environment Variables

### LLM Provider

```bash
# Use non-Ollama provider
export LLM__STUDENT__USE_OLLAMA=false
export LLM__STUDENT__MODEL="gpt-4"
export OPENAI_API_KEY="sk-..."

# Ollama URLs
export OLLAMA_STUDENT_BASE_URL="http://localhost:11434"
export OLLAMA_TEACHER_BASE_URL="http://localhost:11434"
export OLLAMA_BASE_URL="http://localhost:11434"  # Fallback if specific URLs not set
```

### Paths

```bash
export PATHS__PDF_DIR="data/my_pdfs"
export PATHS__SPLITS_FILE="data/splits/mytask.json"
```

### Optimization

```bash
export OPTIMIZATION__NUM_TRIALS="50"
export OPTIMIZATION__USE_CACHE="true"
```

### Logging

```bash
export LOG_LEVEL="DEBUG"
```

### MLflow

```bash
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
```

### DSPy Cache

```bash
export DSPY_CACHE_DIR="~/.cache/dspy"
```

### API Keys (required for non-Ollama providers)

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

### Environment Selection

```bash
# Select environment-specific config (e.g., config/dev.yaml, config/prod.yaml)
export AEE_ENV="dev"
```

---

## Task Configuration (YAML)

Tasks are defined in `src/aee/domain/tasks/{task_name}/task.yaml`:

```yaml
name: mytask
description: Extract my domain experiments

fields:
  field_name:
    type: str
    description: "Field description"
    required: true
    alt_names:
      - alternative_name

compare_fields:
  - field_name
float_tolerance: 0.05

instruction_file: config/initial_instructions/mytask.txt
```

> **Full guide:** [Adding Tasks](adding_tasks.md)

---

## Quick Reference

| Setting | Env Variable | YAML Path |
|---------|--------------|-----------|
| LLM Model | `LLM__STUDENT__MODEL` | `llm.student.model` |
| LLM Temperature | `LLM__STUDENT__TEMPERATURE` | `llm.student.temperature` |
| LLM Cache | `LLM__STUDENT__ENABLE_CACHE` | `llm.student.enable_cache` |
| Num Trials | `OPTIMIZATION__NUM_TRIALS` | `optimization.num_trials` |
| Num Candidates | `OPTIMIZATION__NUM_CANDIDATES` | `optimization.num_candidates` |
| Metric Threshold | `OPTIMIZATION__METRIC_THRESHOLD` | `optimization.metric_threshold` |
| PDF Dir | `PATHS__PDF_DIR` | `paths.pdf_dir` |
| Splits File | `PATHS__SPLITS_FILE` | `paths.splits_file` |
| Task Name | *(not configurable via env)* | `task.name` |
| Log Level | `LOG_LEVEL` | `project.log_level` |
| MLflow URI | `MLFLOW_TRACKING_URI` | `mlflow_tracking_uri` |
| DSPy Cache | `DSPY_CACHE_DIR` | `dspy_cache_dir` |
| Ollama Student URL | `OLLAMA_STUDENT_BASE_URL` | `llm.student.ollama.ollama_base_url` |
| Ollama Teacher URL | `OLLAMA_TEACHER_BASE_URL` | `llm.teacher.ollama.ollama_base_url` |
| OpenAI API Key | `OPENAI_API_KEY` | (not configurable in YAML) |
| Anthropic API Key | `ANTHROPIC_API_KEY` | (not configurable in YAML) |
| Gemini API Key | `GEMINI_API_KEY` | (not configurable in YAML) |

> **Note:** Task configuration (`task.name`, `task.evaluation.*`) загружается **только из YAML файлов** и не может быть переопределён через environment variables.
