"""
src/kg/kg_builder.py
Knowledge Base construction, entity linking, predicate alignment & SPARQL expansion.
Domain: Science-Fiction (authors & works)
"""

import requests
import urllib.parse
import time
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD
from collections import Counter

# ── Namespaces ──
PRIV = Namespace("http://myproject.org/resource/")
PRED = Namespace("http://myproject.org/predicate/")
DBO  = Namespace("http://dbpedia.org/ontology/")
DBR  = Namespace("http://dbpedia.org/resource/")


def init_graph() -> Graph:
    """Initialize and return an empty RDF graph with bound namespaces."""
    kg = Graph()
    kg.bind("priv", PRIV)
    kg.bind("pred", PRED)
    kg.bind("dbo",  DBO)
    kg.bind("dbr",  DBR)
    return kg


def fetch_books_from_api(subject: str = "science_fiction", limit: int = 35) -> list:
    """Fetch works from the Open Library Subjects API."""
    url = f"https://openlibrary.org/subjects/{subject}.json?limit={limit}"
    print(f"Fetching: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json().get("works", [])
    except Exception as e:
        print(f"Erreur API : {e}")
        return []


def build_initial_kg(books_data: list, kg: Graph) -> Graph:
    """
    Build the initial private KB from Open Library works data.
    Adds Book and Author entities with basic triples.
    """
    for book in books_data:
        raw_title  = book.get("title", "Unknown")
        safe_title = urllib.parse.quote(raw_title.replace(" ", "_"))
        book_uri   = PRIV[safe_title]

        kg.add((book_uri, RDF.type,   PRIV.Book))
        kg.add((book_uri, PRED.title, Literal(raw_title, datatype=XSD.string)))

        if "first_publish_year" in book:
            kg.add((book_uri, PRED.firstPublishYear,
                    Literal(book["first_publish_year"], datatype=XSD.integer)))

        for author_data in book.get("authors", []):
            raw_name   = author_data.get("name", "Unknown")
            safe_name  = urllib.parse.quote(raw_name.replace(" ", "_"))
            author_uri = PRIV[safe_name]

            kg.add((author_uri, RDF.type,       PRIV.Author))
            kg.add((author_uri, PRED.wroteBook, book_uri))
            kg.add((author_uri, PRED.name,      Literal(raw_name, datatype=XSD.string)))

    return kg


def link_entity_sparql(wiki_url: str):
    """
    Verify a DBpedia URI existence via SPARQL ASK.
    Returns (dbpedia_uri, confidence) or (None, 0.0).
    """
    page_name   = wiki_url.split("/wiki/")[-1]
    dbpedia_uri = f"http://dbpedia.org/resource/{page_name}"
    url         = "https://dbpedia.org/sparql"
    query       = f"ASK {{ <{dbpedia_uri}> ?p ?o . }}"
    params      = {"query": query, "format": "application/json"}

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        if r.json().get("boolean", False):
            return dbpedia_uri, 1.0
    except Exception as e:
        print(f"Erreur pour {dbpedia_uri} : {e}")
    return None, 0.0


def link_entity_to_dbpedia(entity_label: str):
    """
    Link a plain entity label to DBpedia via SPARQL ASK.
    Returns (dbpedia_uri, confidence) or (None, 0.0).
    """
    page_name   = entity_label.replace(" ", "_")
    dbpedia_uri = f"http://dbpedia.org/resource/{page_name}"
    url         = "https://dbpedia.org/sparql"
    query       = f"ASK {{ <{dbpedia_uri}> ?p ?o . }}"
    params      = {"query": query, "format": "application/json"}

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        if r.json().get("boolean", False):
            return dbpedia_uri, 1.0
    except Exception:
        pass
    return None, 0.0


def search_dbo_properties(keyword: str) -> list:
    """Search DBpedia ontology for properties matching a keyword."""
    url   = "https://dbpedia.org/sparql"
    query = f"""
    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?property ?label WHERE {{
        ?property a rdf:Property .
        FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
        FILTER(CONTAINS(LCASE(STR(?property)), LCASE("{keyword}")))
        OPTIONAL {{ ?property rdfs:label ?label . FILTER(LANG(?label) = "en") }}
    }}
    LIMIT 10
    """
    params = {"query": query, "format": "application/json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return [
            {"URI": b["property"]["value"],
             "Label": b.get("label", {}).get("value", "(no label)")}
            for b in r.json()["results"]["bindings"]
        ]
    except Exception as e:
        print(f"Erreur : {e}")
        return []


def get_scifi_anchors(limit: int = 300) -> list:
    """Fetch DBpedia URIs of Sci-Fi writers as expansion anchors."""
    url   = "https://dbpedia.org/sparql"
    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbr: <http://dbpedia.org/resource/>
    SELECT DISTINCT ?author WHERE {{
        ?author a dbo:Writer .
        ?author dbo:genre dbr:Science_fiction .
    }}
    LIMIT {limit}
    """
    params = {"query": query, "format": "application/json"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return [b["author"]["value"] for b in r.json()["results"]["bindings"]]
    except Exception as e:
        print(f"Erreur : {e}")
        return []


def fetch_2hop(dbpedia_uri: str) -> Graph:
    """
    Fetch 2-hop triples from DBpedia for a given anchor URI.
    1-hop: author properties
    2-hop: author → notableWork → work properties
    """
    url      = "https://dbpedia.org/sparql"
    excluded = (
        "dbo:abstract, "
        "<http://dbpedia.org/property/wikiPageUsesTemplate>, "
        "<http://www.w3.org/ns/prov#wasDerivedFrom>, "
        "<http://xmlns.com/foaf/0.1/isPrimaryTopicOf>"
    )
    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    CONSTRUCT {{
        <{dbpedia_uri}> ?p ?o .
        ?work ?work_p ?work_o .
    }}
    WHERE {{
        {{ <{dbpedia_uri}> ?p ?o .
           FILTER(?p NOT IN ({excluded})) }}
        UNION
        {{ <{dbpedia_uri}> dbo:notableWork ?work .
           ?work ?work_p ?work_o .
           FILTER(?work_p NOT IN ({excluded})) }}
    }}
    LIMIT 6000
    """
    params = {"query": query, "format": "text/turtle"}
    tmp = Graph()
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        tmp.parse(data=r.text, format="turtle")
    except Exception:
        pass
    return tmp


def expand_kg(anchors: list, sleep: float = 0.1) -> Graph:
    """
    Expand the KG via 2-hop SPARQL queries from anchor URIs.
    Returns the expanded Graph.
    """
    final_kg = Graph()
    for idx, anchor in enumerate(anchors, 1):
        if idx % 10 == 0:
            print(f"  {idx}/{len(anchors)} — triplets : {len(final_kg):,}")
        final_kg += fetch_2hop(anchor)
        time.sleep(sleep)
    return final_kg


def clean_kg(kg: Graph, top_n_predicates: int = 150) -> Graph:
    """
    Clean the expanded KG:
    - Keep only URI→URI triples
    - Keep only DBpedia entities
    - Keep only the top N most frequent predicates
    """
    pred_counts    = Counter(str(p) for _, p, _ in kg)
    top_predicates = {p for p, _ in pred_counts.most_common(top_n_predicates)}

    clean = Graph()
    for s, p, o in kg:
        if (isinstance(s, URIRef) and isinstance(o, URIRef)
                and "dbpedia.org" in str(s)
                and "dbpedia.org" in str(o)
                and str(p) in top_predicates):
            clean.add((s, p, o))
    return clean


def print_kg_stats(kg: Graph, label: str = "KG"):
    """Print entity/predicate/triple statistics for a graph."""
    all_ents  = set(kg.subjects()) | {o for o in kg.objects() if isinstance(o, URIRef)}
    all_preds = set(kg.predicates())
    print(f"\n{'='*50}")
    print(f"{label}")
    print(f"{'='*50}")
    print(f"Triplets   : {len(kg):>8,}  (cible : 50k–200k)")
    print(f"Entités    : {len(all_ents):>8,}  (cible : 5k–30k)")
    print(f"Prédicats  : {len(all_preds):>8,}  (cible : 50–200)")
    print(f"{'='*50}")
