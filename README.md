# AutoEvoExtractor

AutoEvoExtractor (AEE) is an evolutionary multi-agent system designed for structured information extraction from scientific literature. It utilizes DSPy and MIPROv2 to automatically optimize prompts and extraction strategies, adapting to complex domains like Nanochemistry.

## Installation

The project uses Conda for environment management.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AutoEvoExtractor
    ```

2.  **Create the environment:**
    ```bash
    conda env create -f environment.yml
    conda activate aee
    ```

## Configuration

Create a `.env` file in the root directory to configure the LLM provider (Google Gemini is the default).

```ini
GEMINI_API_KEY=your_api_key_here
```

You can customize model parameters in `src/aee/core/config.py` or via environment variables (e.g., `STUDENT_MODEL`, `TEACHER_MODEL`).

## Usage: GUI

The primary way to interact with AutoEvoExtractor is through the Streamlit dashboard.

Start the application:

```bash 
streamlit run app/Home.py
```

The interface consists of four main sections:

1. Home: System status dashboard, API key configuration, and quick start guide.
2. Training Studio:
   - Library Manager: Upload and parse PDF articles to build your training corpus.
   - Optimizer: Run evolutionary algorithms (MIPROv2) on the library data to generate optimized agents.
3. Playground: An interactive sandbox to test agents (Zero-shot or Optimized) on individual files. Includes real-time Chain-of-Thought visualization and single-document metric calculation against Ground Truth.
4. Evaluation: Benchmarking tool to calculate aggregate Precision, Recall, and F1-Score on the test split.

## Usage: Command Line

The workflow consists of five sequential stages. All scripts are located in the `scripts/` directory.

### 1. Download Data

Downloads the ground truth dataset (ChemX/Nanozymes) from Hugging Face.

```bash
python scripts/download_data.py --task nanozymes
```

### 2. Data Splitting

Generates a splits.json file to strictly separate training and testing data. This ensures reproducible experiments and prevents data leakage during optimization.

```bash    
python scripts/create_splits.py --gt data/ground_truth/nanozymes.csv
```

### 3. Ingestion (PDF Parsing)

Converts raw PDF files into structured JSON documents containing Markdown text and metadata.

```bash 
python scripts/ingest.py --input data/raw --output data/processed --parser docling
```

### 4. Evolutionary Optimization

Optimizes the extraction agent using DSPy.
**Note:** A splits.json file defining train and test sets is required to prevent data leakage.

```bash    
python scripts/optimize.py \
  --task nanozymes \
  --train_size 20 \
  --split_file data/splits.json \
  --output data/artifacts/optimized_agent.json
```

### 5. Inference

Runs the optimized agent (or a zero-shot baseline) on the dataset.

```bash
python scripts/predict.py \
  --task nanozymes \
  --agent_path data/artifacts/optimized_agent.json
```

### 6. Evaluation

Calculates Precision, Recall, and F1-Score by comparing predictions against the Ground Truth using the Hungarian Algorithm for entity alignment.

```bash
python scripts/benchmark.py \
  --task nanozymes \
  --split_file data/splits.json
```

## Project Structure

```text
.
├── app/                    # Streamlit Web Application
│   ├── Home.py             # Entry point and Dashboard
│   └── pages/              # Application modules
│       ├── Evaluation.py
│       ├── Playground.py
│       └── Training_Studio.py
├── data/                   # Data storage (gitignored)
├── scripts/                # CLI Scripts (ETL, Inference, Eval)
├── src/
│   └── aee/                # Core Package
│       ├── agents/         # DSPy modules and logic
│       ├── core/           # Config, logging, types
│       ├── eval/           # Metrics and matching logic
│       ├── ingestion/      # PDF parsers (Docling, Marker, etc.)
│       ├── tasks/          # Task definitions (Nanozymes, etc.)
│       └── utils/          # Shared utilities (I/O, Dataset prep)
├── environment.yml         # Conda environment definition
└── README.md               # Project documentation
```