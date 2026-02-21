# Architecture

System architecture of AutoEvoExtractor.

## Overview

AutoEvoExtractor uses a simplified architecture optimized for R&D experimentation.

**Key Design Decisions:**

1. **Task Config as Single Source of Truth** — All task definitions in YAML
2. **Dynamic Model Generation** — Pydantic models generated at runtime
3. **Functional Infrastructure** — Functions over classes where appropriate
4. **YAML Manifests** — Declarative task configuration

---

## Architecture Diagram

```
┌─────────────────────────────────────┐
│ INTERFACE (CLI)                     │
│ - parse.py, optimize.py, extract.py │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ APPLICATION (Use Cases)             │
│ - optimize_agent()                  │
│ - extract_batch()                   │
│ - parse_documents()                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ DOMAIN (Task Config + Dynamic)      │
│ - TaskConfig (dataclass)            │
│ - *.yaml manifests                  │
│ - create_experiment_model(config)   │
│ - create_signature(config, model)   │
│ - TaskRegistry                      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ INFRASTRUCTURE (Storage/LLM/Parsers)│
│ - save_agent(), load_agent()        │
│ - load_ground_truth()               │
│ - load_split(), load_all_splits()   │
│ - create_lm(), setup_llm()          │
│ - DoclingParser, MarkerParser       │
└─────────────────────────────────────┘
```

---

## Components

### Interface Layer

CLI scripts for user interaction:

| Script | Purpose |
|--------|---------|
| `parse.py` | Parse PDFs to JSON |
| `optimize.py` | Optimize agent via MIPROv2 |
| `extract.py` | Extract data using agent |

### Application Layer

Use cases as functions:

| Use Case | Description |
|----------|-------------|
| `optimize_agent()` | Full optimization cycle |
| `extract_batch()` | Batch extraction |
| `parse_documents()` | Document parsing |

### Domain Layer

Task configuration and dynamic generation:

| Component | Purpose |
|-----------|---------|
| `TaskConfig` | Task definition dataclass |
| `FieldSpec` | Field specification |
| `create_experiment_model()` | Generate Pydantic model |
| `create_signature()` | Generate DSPy signature |
| `TaskRegistry` | Task registry with component caching (lazy loading) |

### Infrastructure Layer

Utility functions:

| Category | Functions |
|----------|-----------|
| Storage | `save_agent()`, `load_agent()`, `load_ground_truth()` |
| LLM | `create_lm()`, `setup_student()`, `setup_teacher()` |
| Parsers | `DoclingParser`, `MarkerParser`, `get_parser()` |

---

## Data Flow

### Optimization Flow

```
Ground Truth CSV ─┬─→ DatasetBuilder ─→ Training Dataset
                  │
Splits JSON ──────┘
                        │
                        ▼
                  MIPROv2 Optimization
                        │
                        ▼
                  Agent JSON (saved)
```

### Extraction Flow

```
Agent JSON ─┬─→ BatchPrediction ─→ Extractions JSON
            │
Parsed JSON ┘
```

---

## Task System

### YAML-Based Tasks

Tasks defined in `src/aee/domain/tasks/{task_name}/task.yaml`:

```yaml
name: nanozymes
fields:
  formula:
    type: str
    required: true
compare_fields:
  - formula
  - activity
```

### Dynamic Generation

From YAML, system generates:

1. **Pydantic Model** — `create_experiment_model()`
2. **DSPy Signature** — `create_signature()`
3. **Row Converter** — `create_row_converter()`

### Task Registry

Central registry for task management:

```python
from aee.domain.tasks import get_task

task = get_task("nanozymes")
# Returns: {config, experiment_model, output_model, signature, row_converter}
```

---

## Configuration System

### Priority Order

1. Environment variables (`.env`, `AEE__*`)
2. CLI arguments (`--config`, `--run-name`)
3. YAML files (`config/default.yaml`)
4. Internal defaults

### Example

```bash
# Environment (highest priority)
export OPTIMIZATION__NUM_TRIALS="50"

# CLI
python scripts/optimize.py --config config/fast.yaml

# YAML (config/fast.yaml)
optimization:
  num_trials: 10
```

---

## Key Design Patterns

### 1. Configuration-Backed Design

All task logic derived from YAML configuration:

```
YAML → TaskConfig → Dynamic Models → Runtime
```

### 2. Functional Infrastructure

Simple functions instead of complex classes:

```python
# Instead of:
repo = AgentRepository(agents_dir)
repo.save_agent(agent, metadata)

# Use:
save_agent(agent=agent, task_name="nanozymes", metadata=metadata)
```

### 3. Lazy Loading

Models and signatures generated on first access:

```python
task = get_task("nanozymes")
# Models not generated until accessed
model = task["experiment_model"]  # ← Generated here
```

---

## Extension Points

### Adding New Tasks

1. Create `src/aee/domain/tasks/{task_name}/task.yaml`
2. Create `config/initial_instructions/{task_name}.txt`
3. Create `data/ground_truth/{task_name}.csv`
4. Create `data/splits/{task_name}.json`

[Full guide →](adding_tasks.md)

---

## Testing Architecture

### Test Layers

```
┌─────────────────┐
│ E2E Tests       │  ← Full workflow (slow)
├─────────────────┤
│ Integration     │  ← Component interaction
├─────────────────┤
│ Unit Tests      │  ← Individual components
└─────────────────┘
```

### Test Locations

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Component tests |
| `tests/integration/` | Interaction tests |
| `tests/e2e/` | Workflow tests |

---

## Version History

| Version | Changes |
|---------|---------|
| 2.0 | YAML-based tasks, removed TaskDefinition |
| 1.0 | Initial release with TaskDefinition |

---

## Related Documents

- [Configuration Reference](configuration.md)
- [Adding Tasks](adding_tasks.md)
- [CLI Reference](cli_reference.md)
- [Data Artifacts](data_artifacts.md)
