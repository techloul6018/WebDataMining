"""
src/rag/rag.py
RAG pipeline: RDF graph loading, schema summary, NL->SPARQL generation,
self-repair, and baseline comparison.
"""

import re
import requests
from typing import List, Tuple
from rdflib import Graph

# ── Configuration ──
OLLAMA_URL      = "http://localhost:11434/api/generate"
GEMMA_MODEL     = "gemma:2b"
MAX_PREDICATES  = 80
MAX_CLASSES     = 40
SAMPLE_TRIPLES  = 20
CODE_BLOCK_RE   = re.compile(r"```(?:sparql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

# ── Code fence variables (avoid backtick issues in f-strings) ──
FENCE_OPEN  = "```sparql"
FENCE_CLOSE = "```"


# ── 0. LLM call ──

def ask_local_llm(prompt: str, model: str = GEMMA_MODEL) -> str:
    """Send a prompt to a local Ollama model and return the response."""
    payload  = {"model": model, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")
    return response.json().get("response", "")


# ── 1. Load RDF graph ──

def load_graph(ttl_path: str) -> Graph:
    """Load an RDF graph from a Turtle file."""
    g = Graph()
    g.parse(ttl_path, format="turtle")
    print(f"Loaded {len(g)} triples from {ttl_path}")
    return g


# ── 2. Schema summary ──

def get_prefix_block(g: Graph) -> str:
    defaults = {
        "rdf":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd":  "http://www.w3.org/2001/XMLSchema#",
        "owl":  "http://www.w3.org/2002/07/owl#",
    }
    ns_map = {p: str(ns) for p, ns in g.namespace_manager.namespaces()}
    for k, v in defaults.items():
        ns_map.setdefault(k, v)
    return "\n".join(sorted(f"PREFIX {p}: <{ns}>" for p, ns in ns_map.items()))


def list_distinct_predicates(g: Graph, limit: int = MAX_PREDICATES) -> List[str]:
    q = f"SELECT DISTINCT ?p WHERE {{ ?s ?p ?o . }} LIMIT {limit}"
    return [str(row.p) for row in g.query(q)]


def list_distinct_classes(g: Graph, limit: int = MAX_CLASSES) -> List[str]:
    q = f"SELECT DISTINCT ?cls WHERE {{ ?s a ?cls . }} LIMIT {limit}"
    return [str(row.cls) for row in g.query(q)]


def sample_triples(g: Graph, limit: int = SAMPLE_TRIPLES) -> List[Tuple[str, str, str]]:
    q = f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o . }} LIMIT {limit}"
    return [(str(r.s), str(r.p), str(r.o)) for r in g.query(q)]


def build_schema_summary(g: Graph) -> str:
    """Build a compact schema summary for the LLM prompt."""
    prefixes     = get_prefix_block(g)
    preds        = list_distinct_predicates(g)
    clss         = list_distinct_classes(g)
    samples      = sample_triples(g)
    pred_lines   = "\n".join(f"- {p}" for p in preds)
    cls_lines    = "\n".join(f"- {c}" for c in clss)
    sample_lines = "\n".join(f"- {s} {p} {o}" for s, p, o in samples)
    return (
        prefixes + "\n"
        "# Predicates (sampled, unique up to " + str(MAX_PREDICATES) + ")\n"
        + pred_lines + "\n"
        "# Classes / rdf:type (sampled, unique up to " + str(MAX_CLASSES) + ")\n"
        + cls_lines + "\n"
        "# Sample triples (up to " + str(SAMPLE_TRIPLES) + ")\n"
        + sample_lines
    )


# ── 3. NL -> SPARQL ──

def extract_sparql_from_text(text: str) -> str:
    """Extract the first SPARQL code block from LLM output."""
    m = CODE_BLOCK_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def generate_sparql(question: str, schema_summary: str) -> str:
    """Generate a SPARQL query from a natural language question."""
    prompt = (
        "You are a SPARQL generator for a DBpedia-based RDF graph.\n"
        "Return ONLY a SPARQL SELECT query in a " + FENCE_OPEN + " code block.\n"
        "Never write explanations.\n"
        "Use ONLY dbo: and dbr: prefixes.\n"
        "NEVER use wdt:, wd:, wikibase:, or any Wikidata prefixes.\n\n"
        "EXAMPLES:\n\n"
        "Question: What are the works of Isaac Asimov?\n"
        + FENCE_OPEN + "\n"
        "PREFIX dbo: <http://dbpedia.org/ontology/>\n"
        "PREFIX dbr: <http://dbpedia.org/resource/>\n"
        "SELECT ?work WHERE {\n"
        "  dbr:Isaac_Asimov dbo:wikiPageWikiLink ?work .\n"
        "} LIMIT 10\n"
        + FENCE_CLOSE + "\n\n"
        "Question: Who was born in Chicago?\n"
        + FENCE_OPEN + "\n"
        "PREFIX dbo: <http://dbpedia.org/ontology/>\n"
        "PREFIX dbr: <http://dbpedia.org/resource/>\n"
        "SELECT ?person WHERE {\n"
        "  ?person dbo:birthPlace dbr:Chicago .\n"
        "}\n"
        + FENCE_CLOSE + "\n\n"
        "Question: Which authors write in the Science Fiction genre?\n"
        + FENCE_OPEN + "\n"
        "PREFIX dbo: <http://dbpedia.org/ontology/>\n"
        "PREFIX dbr: <http://dbpedia.org/resource/>\n"
        "SELECT ?author WHERE {\n"
        "  ?author dbo:genre dbr:Science_fiction .\n"
        "} LIMIT 20\n"
        + FENCE_CLOSE + "\n\n"
        "Question: What is the genre of Gordon R. Dickson?\n"
        + FENCE_OPEN + "\n"
        "PREFIX dbo: <http://dbpedia.org/ontology/>\n"
        "PREFIX dbr: <http://dbpedia.org/resource/>\n"
        "SELECT ?genre WHERE {\n"
        "  dbr:Gordon_R._Dickson dbo:genre ?genre .\n"
        "}\n"
        + FENCE_CLOSE + "\n\n"
        "Question: What is the movement of Isaac Asimov?\n"
        + FENCE_OPEN + "\n"
        "PREFIX dbo: <http://dbpedia.org/ontology/>\n"
        "PREFIX dbr: <http://dbpedia.org/resource/>\n"
        "SELECT ?movement WHERE {\n"
        "  dbr:Isaac_Asimov dbo:movement ?movement .\n"
        "}\n"
        + FENCE_CLOSE + "\n\n"
        "SCHEMA SUMMARY:\n"
        + schema_summary + "\n\n"
        "Now answer ONLY with a SPARQL query — no text, no explanation:\n"
        "Question: " + question + "\n"
        + FENCE_OPEN + "\n"
    )

    raw = FENCE_OPEN + "\n" + ask_local_llm(prompt)
    return extract_sparql_from_text(raw)


# ── 4. Execute SPARQL + self-repair ──

def run_sparql(g: Graph, query: str) -> Tuple[List[str], List[Tuple]]:
    """Execute a SPARQL query on an rdflib Graph."""
    res   = g.query(query)
    vars_ = [str(v) for v in res.vars]
    rows  = [tuple(str(cell) for cell in r) for r in res]
    return vars_, rows


def repair_sparql(schema_summary: str, question: str,
                  bad_query: str, error_msg: str) -> str:
    """Ask the LLM to fix a broken SPARQL query."""
    prompt = (
        "The previous SPARQL failed. Fix it using the schema.\n"
        "Use ONLY dbo: and dbr: prefixes. NEVER use wdt: or wd:.\n"
        "Return ONLY the corrected SPARQL in a " + FENCE_OPEN + " code block.\n\n"
        "SCHEMA SUMMARY:\n" + schema_summary + "\n\n"
        "QUESTION: " + question + "\n"
        "BAD SPARQL:\n" + bad_query + "\n"
        "ERROR: " + error_msg + "\n"
    )
    raw = FENCE_OPEN + "\n" + ask_local_llm(prompt)
    return extract_sparql_from_text(raw)


# ── 5. Full RAG pipeline ──

def answer_with_sparql_generation(g: Graph, schema_summary: str,
                                   question: str, try_repair: bool = True) -> dict:
    """
    Full RAG pipeline: generate SPARQL -> execute -> self-repair if needed.
    Returns a dict with query, vars, rows, repaired, error.
    """
    sparql = generate_sparql(question, schema_summary)
    try:
        vars_, rows = run_sparql(g, sparql)
        return {"query": sparql, "vars": vars_, "rows": rows,
                "repaired": False, "error": None}
    except Exception as e:
        err = str(e)
        if try_repair:
            repaired = repair_sparql(schema_summary, question, sparql, err)
            try:
                vars_, rows = run_sparql(g, repaired)
                return {"query": repaired, "vars": vars_, "rows": rows,
                        "repaired": True, "error": None}
            except Exception as e2:
                return {"query": repaired, "vars": [], "rows": [],
                        "repaired": True, "error": str(e2)}
        return {"query": sparql, "vars": [], "rows": [],
                "repaired": False, "error": err}


# ── 6. Baseline (no RAG) ──

def answer_no_rag(question: str) -> str:
    """Answer a question directly with the LLM, without graph access."""
    prompt = "Answer the following question as best as you can:\n\n" + question
    return ask_local_llm(prompt)


# ── 7. Display results ──

def pretty_print_result(result: dict):
    """Pretty-print a RAG pipeline result."""
    if result.get("error"):
        print("\n[Execution Error]", result["error"])
    print("\n[SPARQL Query Used]")
    print(result["query"])
    print("\n[Repaired?]", result["repaired"])
    vars_ = result.get("vars", [])
    rows  = result.get("rows", [])
    if not rows:
        print("\n[No rows returned]")
        return
    print("\n[Results]")
    print(" | ".join(vars_))
    for r in rows[:20]:
        print(" | ".join(r))
    if len(rows) > 20:
        print(f"... (showing 20 of {len(rows)})")