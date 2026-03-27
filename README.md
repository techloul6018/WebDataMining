# 🕷️ Web Crawling & Data Extraction Pipeline


A modular pipeline for **crawling the web**, **extracting structured information**, building a **Knowledge Graph**, and querying it through a **RAG interface**. Each stage is independently runnable and feeds into the next.

---

## 📋 Table of Contents

- [Project Structure](#project-structure)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [How to Run Each Module](#how-to-run-each-module)
  - [1. Crawl](#1-crawl)
  - [2. Information Extraction (IE)](#2-information-extraction-ie)
  - [3. Knowledge Graph (KG)](#3-knowledge-graph-kg)
  - [4. Reasoning](#4-reasoning)
  - [5. KG Embeddings (KGE)](#5-kg-embeddings-kge)
  - [6. RAG](#6-rag)
- [RAG Demo](#rag-demo)
- [KG Artifacts](#kg-artifacts)
- [Screenshot](#screenshot)

---

## 🗂 Project Structure

```
project-root/
├─ src/
│  ├─ crawl/       # Web crawling & document fetching
│  ├─ ie/          # Information extraction (NER, relation extraction)
│  ├─ kg/          # Knowledge graph construction & serialisation
│  ├─ reason/      # Ontology reasoning & inference
│  ├─ kge/         # Knowledge graph embeddings
│  └─ rag/         # Retrieval-Augmented Generation interface
├─ data/
│  ├─ samples/     # Sample seed URLs and input documents
│  └─ README.md
├─ kg_artifacts/
│  ├─ ontology.ttl
│  ├─ expanded.nt
│  └─ alignment.ttl
├─ reports/
│  └─ final_report.pdf
├─ notebooks/      # Exploratory Jupyter notebooks
├─ README.md
├─ requirements.txt
├─ .gitignore
└─ LICENSE
```

---

## ⚙️ Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB |
| Disk | 5 GB free | 20 GB free (crawled data can grow fast) |
| GPU | *(optional)* | CUDA-capable GPU for KGE training & RAG |

> **Note:** All modules run on CPU. A GPU (≥ 8 GB VRAM) is only needed for accelerated KGE training and local LLM inference in the RAG module.

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Install a spaCy model for information extraction

```bash
python -m spacy download en_core_web_sm
```

---

## 🔧 How to Run Each Module

All commands are run from the **project root** with the virtual environment activated.

---

### 1. Crawl

Fetches and stores raw HTML/text documents starting from a list of seed URLs.

```bash
python -m src.crawl.main \
  --seeds data/samples/seeds.txt \
  --output data/raw/ \
  --depth 2
```

| Argument | Description |
|----------|-------------|
| `--seeds` | Text file with one seed URL per line |
| `--output` | Directory to store crawled documents |
| `--depth` | Maximum crawl depth (default: `2`) |

---

### 2. Information Extraction (IE)

Runs named entity recognition and relation extraction over raw crawled documents.

```bash
python -m src.ie.main \
  --input data/raw/ \
  --output data/extracted/ \
  --model en_core_web_sm
```

| Argument | Description |
|----------|-------------|
| `--input` | Directory of raw crawled documents |
| `--output` | Directory to write extracted triples (JSON-L) |
| `--model` | spaCy model name |

---

### 3. Knowledge Graph (KG)

Builds an RDF graph from extracted triples and serialises it to Turtle / N-Triples.

```bash
python -m src.kg.main \
  --input data/extracted/ \
  --ontology kg_artifacts/ontology.ttl \
  --output kg_artifacts/expanded.nt
```

| Argument | Description |
|----------|-------------|
| `--input` | Directory of extracted triples |
| `--ontology` | Base ontology file (`.ttl`) |
| `--output` | Output KG file (`.nt` or `.ttl`) |

---

### 4. Reasoning

Applies OWL/RDFS reasoning to materialise inferred triples from the KG.

```bash
python -m src.reason.main \
  --kg kg_artifacts/expanded.nt \
  --output kg_artifacts/inferred.nt \
  --reasoner owlrl
```

| Argument | Description |
|----------|-------------|
| `--kg` | Input KG file |
| `--output` | Output file with materialised inferences |
| `--reasoner` | Reasoner backend (`owlrl`, `hermit`, `pellet`) |

---

### 5. KG Embeddings (KGE)

Trains entity and relation embeddings (TransE, RotatE, …) on the knowledge graph.

```bash
python -m src.kge.main \
  --kg kg_artifacts/expanded.nt \
  --model RotatE \
  --epochs 500 \
  --output data/embeddings/
```

| Argument | Description |
|----------|-------------|
| `--kg` | Input KG file |
| `--model` | Embedding model (`TransE`, `RotatE`, `ComplEx`) |
| `--epochs` | Training epochs (default: `500`) |
| `--output` | Directory to save trained embeddings |

> A CUDA GPU is automatically used when detected.

---

### 6. RAG

See the [RAG Demo](#rag-demo) section below.

---

## 🤖 RAG Demo

The RAG module answers natural-language questions by retrieving relevant triples from the KG and passing them as context to a language model.

### Prerequisites

Ensure the KG has been built (step 3). Embeddings (step 5) are optional but improve retrieval quality.

### Run the interactive CLI demo

```bash
python -m src.rag.demo \
  --kg kg_artifacts/expanded.nt \
  --embeddings data/embeddings/ \
  --model mistralai/Mistral-7B-Instruct-v0.2
```

Example session:

```
> What websites were crawled and what topics do they cover?

🔍 Retrieving relevant triples...
🧠 Generating answer...

Answer: The pipeline crawled [domain_1] and [domain_2], covering topics such as ...
Sources: <entity_1>, <entity_2>, ...
```

### Run via Jupyter notebook

```bash
jupyter notebook notebooks/rag_demo.ipynb
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--kg` | Path to the KG (`.nt` or `.ttl`) |
| `--embeddings` | Directory with trained KGE embeddings (optional) |
| `--model` | HuggingFace model ID or local path |
| `--top-k` | Number of triples to retrieve per query (default: `5`) |
| `--device` | `cuda` or `cpu` (auto-detected if omitted) |

---

## 🗄 KG Artifacts

Pre-built artifacts are available in `kg_artifacts/`:

| File | Description |
|------|-------------|
| `ontology.ttl` | Base domain ontology (Turtle) |
| `expanded.nt` | Full materialised knowledge graph (N-Triples) |
| `alignment.ttl` | Cross-ontology alignment mappings |

---

## 📸 Screenshot

![RAG demo screenshot](docs/screenshots/rag_demo.png)

---

## 📄 License

This project is licensed under the terms of the [LICENSE](LICENSE) file.
