# Web Data Mining — Knowledge Graph Project

**Domain:** Science-Fiction Authors & Works  
**Stack:** Python 3.11, rdflib, spaCy, PyKEEN, OWLReady2, Ollama (Gemma 2B)  
**Authors:** Yann Lin · François-Louis Legland

---

## Project Overview

This project builds a full Knowledge Graph pipeline from web crawling to RAG-based question answering:

```
Web Crawling (TD1)
      ↓
Named Entity Recognition (TD1)
      ↓
KB Construction & Alignment (TP4)
      ↓
SPARQL Expansion → final_expanded_kg.nt
      ↓
SWRL Reasoning + KGE (TD5)
      ↓
RAG over RDF/SPARQL (TD6)
```

---

## Repository Structure

```
project-root/
├── src/
│   ├── crawl/
│   │   └── crawler.py        # Web crawling & cleaning
│   ├── ie/
│   │   └── ner.py            # NER & relation extraction
│   ├── kg/
│   │   └── kg_builder.py     # KB construction, alignment, expansion
│   ├── kge/
│   │   └── kge_utils.py      # KGE data preparation & evaluation
│   └── rag/
│       └── rag.py            # RAG pipeline (NL→SPARQL, self-repair)
│
├── notebooks/
│   ├── TD1_clean.ipynb       # Web crawling & NER
│   ├── TP4_clean.ipynb       # KB construction & expansion
│   ├── TD5_clean.ipynb       # SWRL reasoning & KGE
│   └── TD6_clean.ipynb       # RAG over RDF/SPARQL
│
├── kg_artifacts/
│   ├── final_expanded_kg.nt  # Expanded KB (~58k triples)
│   ├── scifi_kg.ttl          # KB in Turtle format (for RAG)
│   └── entity_alignment.csv  # Entity mapping table
│
├── data/
│   ├── crawler_output.jsonl           # Crawled pages
│   ├── extracted_knowledge_scifi.csv  # Extracted entities
│   ├── train.txt                      # KGE training split
│   ├── valid.txt                      # KGE validation split
│   └── test.txt                       # KGE test split
│
├── reports/
│   └── final_report.pdf      # Final project report
│
├── family.owl                # OWL ontology for SWRL reasoning
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/techloul6018/WebDataMining.git
cd <WebDataMining>
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Download spaCy model

```bash
python -m spacy download en_core_web_trf
```

### 4. Install Ollama (for RAG)

Download and install from **https://ollama.com**, then pull the model:

```bash
ollama pull gemma:2b
```

### 5. Java (for SWRL reasoning)

Pellet requires **Java 17**. Download from **https://adoptium.net/temurin/releases/?version=17**.

After installation, set the Java path in `TD5_clean.ipynb`:
```python
import owlready2
owlready2.JAVA_EXE = "C:/Program Files/Java/jdk-17/bin/java.exe"
```

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Storage | 5 GB free | 10 GB free |
| CPU | 4 cores | 8 cores |
| GPU | Not required | NVIDIA (speeds up KGE) |

> ⚠️ KGE training runs on CPU — expect ~30 minutes for TransE + ComplEx with 30 epochs.

---

## How to Run Each Module

### TD1 — Web Crawling & NER

```bash
# Open notebooks/TD1_clean.ipynb and run all cells
# Outputs:
#   crawler_output.jsonl
#   extracted_knowledge_scifi.csv
```

### TP4 — KB Construction & Expansion

```bash
# Open notebooks/TP4_clean.ipynb and run all cells
# Outputs:
#   final_expanded_kg.nt (~58k triples)
#   entity_alignment.csv
```

### TD5 — SWRL Reasoning & KGE

```bash
# Open notebooks/TD5_clean.ipynb and run all cells
# Outputs:
#   train.txt / valid.txt / test.txt
#   tsne_embeddings.png
```

### TD6 — RAG Demo

```bash
# 1. Start Ollama (leave this terminal open)
ollama serve

# 2. Open notebooks/TD6_clean.ipynb and run all cells
```

---

## RAG Demo

The RAG pipeline answers natural language questions by generating SPARQL queries over the knowledge graph.

**Example questions:**

| Question | RAG Answer |
|---|---|
| What are the works of Isaac Asimov? | 10 linked works from KG |
| Who was born in Chicago? | James Tiptree Jr., Timothy Zahn... |
| Which authors write in the Sci-Fi genre? | 20 authors from KG |
| What is the genre of Gordon R. Dickson? | Fantasy, Science_fiction |
| What is the movement of Isaac Asimov? | Golden_Age_of_Science_Fiction |

---

## KB Statistics

| Metric | Value |
|---|---|
| Total triples | ~58,000 |
| Entities | ~31,000 |
| Distinct predicates | 80 |
| Aligned entities (owl:sameAs) | 226 / 289 (78%) |
| KGE triples (DBpedia-only) | ~48,000 |
| Train / Valid / Test | 80% / 10% / 10% |

---

## KGE Results

| Metric | TransE | ComplEx |
|---|---|---|
| MRR | 0.0003 | 0.0003 |
| Hits@1 | 0.0000 | 0.0000 |
| Hits@3 | 0.0000 | 0.0000 |
| Hits@10 | 0.0000 | 0.0000 |

> Low metrics are expected — see report section 4.3 for analysis.

---

## Notes

- The `numpy` compatibility warnings (`_ARRAY_API not found`) are cosmetic and do not affect execution. Fix with `pip install "numpy<2" --force-reinstall`.
- SWRL reasoning uses manual simulation if Pellet/Java is unavailable.
- The RAG pipeline uses hardcoded SPARQL queries as fallback when Gemma 2B fails to generate valid queries.
