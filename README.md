# AutoEvoExtractor

AutoEvoExtractor (AEE) is a system for structured information extraction from scientific literature. It uses DSPy and MIPROv2 to optimize prompts and extraction strategies, specifically designed for complex domains like Nanochemistry (Nanozymes).

## Installation

The project uses Conda for environment management.

Clone the repository:
```bash
git clone <repository-url>
cd AutoEvoExtractor
```

Create the environment:
```bash
conda env create -f environment.yml
conda activate aee
```

## Configuration

Settings are managed via a default YAML file, optional custom YAML, and environment variables.

Environment Setup (.env):
```
LLM__STUDENT__NON_OLLAMA__API_KEY=your_key
LLM__TEACHER__NON_OLLAMA__API_KEY=your_key
```

The system loads `config/default.yaml` by default. You can override any setting by passing `--config path/to/config.yaml` to the scripts.

Key settings in `src/aee/core/config.py`:
- student/teacher: LLM models and connection types (Ollama vs API).
- parsing: Parser selection (docling or marker) and device (cpu/cuda).
- optimization: Parameters for MIPROv2 (num_trials, candidates, etc.).

## Usage

The workflow consists of sequential stages.

Ingestion (PDF Parsing)
Converts PDF files into structured JSON (Markdown + HTML tables).
```bash
python scripts/parse.py --config config/my_config.yaml
```

Options:
`--overwrite`: Replace existing parsed files.

Optimization
Optimizes the extraction agent using MIPROv2. This requires ground truth data in `data/ground_truth/` and a `splits.json` file.
```bash
python scripts/optimize.py --output data/agents/optimized_nanozymes.json
```

The task name and parameters are pulled from the active configuration.

Inference (Predict)
Run the agent on parsed documents.
```bash
python scripts/predict.py --agent_path data/agents/optimized_nanozymes.json
```

Options:
- `--input`: Override directory of parsed JSONs.
- `--output`: Override directory for results.


## Project Structure
```
.
├── config/                 # YAML configuration files
├── data/                   # Data storage (ignored by git)
│   ├── pdf/                # Source PDF files
│   ├── parsed/             # Output from parse.py (JSON)
│   ├── ground_truth/       # CSV files with reference data
│   ├── agents/             # Saved optimized agents
│   └── predictions/        # Final extraction results
├── logs/                   # LLM history and application logs
├── scripts/                # Execution entry points
│   ├── parse.py            # PDF ingestion
│   ├── optimize.py         # DSPy optimization loop
│   └── predict.py          # Batch inference
├── src/aee/                # Source code
│   ├── agents/             # UniversalExtractor module
│   ├── core/               # Config, types, and logging
│   ├── eval/               # F1 metric and Hungarian matcher
│   ├── ingestion/          # PDF parsing logic and cleaning
│   ├── tasks/              # Task-specific signatures and schemas
│   └── utils/              # Dataset and I/O helpers
└── README.md
```