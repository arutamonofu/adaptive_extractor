# Data Artifacts Guide

Guide to all files and directories in AutoEvoExtractor.

## Data Pipeline

```
PDFs → Parsed JSON ─┬─→ Optimize → Agent
                    │
Ground Truth CSV ───┘
                    │
Splits JSON ────────┘
                    │
                    └─→ Extract → Results
```

---

## Directory Structure

```
data/
├── pdf/              # Source PDF files (user-provided)
├── parsed/           # Parsed JSON (created by parse.py)
├── ground_truth/     # Training CSV (user-provided)
├── splits/           # Data splits JSON (user-provided)
├── agents/           # Trained agents (created by optimize.py)
└── extractions/      # Results (created by extract.py)
```

---

## Input Files

### 1. PDF Files (`data/pdf/`)

**Format:** PDF documents  
**Created by:** User

Place scientific articles here for processing.

```
data/pdf/
├── paper1.pdf
├── paper2.pdf
└── ...
```

> **Config:** `paths.pdf_dir`

---

### 2. Ground Truth CSV (`data/ground_truth/{task}.csv`)

**Format:** CSV  
**Created by:** User

Training data for optimization.

```csv
filename,formula,activity,length,km_value,km_unit
paper1.pdf,Fe3O4,peroxidase,10,0.05,mM
paper2.pdf,CuO,oxidase,20,0.08,mM
```

**Required columns:**
- `filename` — PDF filename (must match file in `data/pdf/`)
- Task-specific fields (defined in `task.yaml`)

> **Config:** `paths.ground_truth_dir`  
> **Guide:** [Adding Tasks](adding_tasks.md)

---

### 3. Data Splits JSON (`data/splits/{task}.json`)

**Format:** JSON  
**Created by:** User

Defines train/validation/test splits.

```json
{
  "train": ["paper1", "paper2", "paper3"],
  "val": ["paper4"],
  "test": ["paper5", "paper6"]
}
```

> ⚠️ **Important:** Document IDs must match `filename` in ground truth CSV (without `.pdf` extension).

> **Config:** `paths.splits_file`

---

## Generated Files

### 4. Parsed JSON (`data/parsed/`)

**Format:** JSON
**Created by:** `parse.py`

Structured document content.

```json
{
  "text_content": "...",
  "metadata": {
    "source_path": "...",
    "filename": "paper1.pdf",
    "page_count": 10,
    "extra": {
      "parser": "Docling",
      "device": "cpu"
    }
  },
  "tables": [],
  "images": []
}
```

**Structure:**
- `text_content` — Extracted text (hybrid format with markdown tables)
- `metadata` — Document metadata including source path, filename, page count, extra parser info
- `tables` — List of extracted tables (HTML format, parser-dependent)
- `images` — List of extracted image paths or descriptions (parser-dependent)

> **Config:** `paths.parsed_dir`
> **Source:** `aee.domain.entities.ProcessedDocument`

---

### 5. Trained Agents (`data/agents/`)

**Format:** JSON + metadata JSON  
**Created by:** `optimize.py`

Optimized extraction agent.

```
data/agents/
├── nanozymes_v1_20260218.json       # Agent state
└── nanozymes_v1_20260218.meta.json  # Metadata
```

**Metadata example:**
```json
{
  "task_name": "nanozymes",
  "created_at": "2026-02-18T17:58:09",
  "model_version": "mistral-small3.1-24b-128k:latest",
  "metrics": {"f1": 0.74},
  "config_snapshot": {...},
  "git_commit": "abc1234",
  "description": "Optimized with 70 trials",
  "initial_instruction_file": "config/initial_instructions/nanozymes_sota.txt",
  "instruction_hash": "a1b2c3d4e5f6"
}
```

**Fields:**
- `task_name` — Task this agent was trained for
- `created_at` — ISO timestamp of creation
- `model_version` — LLM model used
- `metrics` — Performance metrics (F1, precision, recall)
- `config_snapshot` — Configuration used during training
- `git_commit` — Git commit hash at creation (optional)
- `description` — Human-readable description (optional)
- `initial_instruction_file` — Path to initial instruction (optional)
- `instruction_hash` — SHA256 hash (first 12 chars) of instruction (optional)

> **Config:** `paths.agents_dir`
> **Source:** `aee.infrastructure.storage.agents_fn.AgentMetadata`

---

### 6. Extraction Results (`data/extractions/`)

**Format:** JSON
**Created by:** `extract.py`

Extracted data per document.

```json
{
  "extraction": {
    "experiments": [
      {
        "formula": "Fe3O4",
        "activity": "peroxidase",
        "length": 10.0,
        "km_value": 0.05
      }
    ]
  },
  "source_metadata": {
    "filename": "paper1.pdf",
    "document_id": "paper1"
  }
}
```

**Structure:**
- `extraction.experiments` — List of extracted experiments
- `source_metadata` — Optional metadata from the source document

> **Note:** The extraction loader supports multiple formats for compatibility:
> - `{"extraction": {"experiments": [...]}}` — Standard format
> - `{"experiments": [...]}` — Direct experiments list
> - `{"extracted_data": {"experiments": [...]}}` — Alternative format
> - `[...]` — Direct list of experiments
>
> See `aee.infrastructure.storage.extractions.ExtractionRepository._extract_experiments()` for details.

> **Config:** `paths.extractions_dir`
> **Source:** `aee.infrastructure.storage.extractions.ExtractionRepository.save()`

---

## Task Configuration

### Task YAML (`src/aee/domain/tasks/{task_name}/task.yaml`)

**Format:** YAML  
**Created by:** User

Defines extraction task.

```yaml
name: nanozymes
description: Extract nanozyme experiments

fields:
  formula:
    type: str
    description: "Chemical formula"
    required: true

compare_fields:
  - formula
  - activity
float_tolerance: 0.05

instruction_file: config/initial_instructions/nanozymes_sota.txt
```

> **Guide:** [Adding Tasks](adding_tasks.md)

---

## Instruction Files

### Initial Instructions (`config/initial_instructions/`)

**Format:** TXT  
**Created by:** User

Base instructions for DSPy optimization.

```
config/initial_instructions/
└── nanozymes_sota.txt
```

> **Referenced in:** `task.yaml` → `instruction_file`

---

## Quick Reference

| File | Location | Created By | Required |
|------|----------|------------|----------|
| PDFs | `data/pdf/` | User | Yes (for parsing) |
| Ground Truth | `data/ground_truth/` | User | Yes (for optimization) |
| Splits | `data/splits/` | User | Yes (for optimization) |
| Parsed JSON | `data/parsed/` | `parse.py` | No (auto-generated) |
| Agent | `data/agents/` | `optimize.py` | No (auto-generated) |
| Extractions | `data/extractions/` | `extract.py` | No (auto-generated) |
| Task YAML | `src/aee/domain/tasks/` | User | Yes (for new tasks) |
| Instructions | `config/initial_instructions/` | User | Yes (for optimization) |
