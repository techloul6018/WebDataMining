"""
src/kge/kge_utils.py
Knowledge Graph Embedding utilities: data preparation, training, evaluation.
"""

import random
from rdflib import Graph, URIRef


def load_and_filter_kg(nt_file: str) -> list:
    """
    Load a .nt KG file and filter to DBpedia-only URI→URI triples.
    Returns a deduplicated list of (subject, predicate, object) tuples.
    """
    kg = Graph()
    kg.parse(nt_file, format="nt")
    print(f"KG chargé : {len(kg):,} triplets")

    clean_triplets = list(set(
        (str(s), str(p), str(o))
        for s, p, o in kg
        if (isinstance(s, URIRef) and isinstance(o, URIRef)
            and "dbpedia.org" in str(s)
            and "dbpedia.org" in str(o))
    ))
    print(f"Triplets après filtrage DBpedia : {len(clean_triplets):,}")
    return clean_triplets


def split_triplets(clean_triplets: list, seed: int = 42):
    """
    Split triplets into train/valid/test (80/10/10).
    Ensures no entity leakage: triples with unseen entities go to train.
    Returns (train_data, clean_valid, clean_test).
    """
    random.seed(seed)
    random.shuffle(clean_triplets)

    total      = len(clean_triplets)
    train_data = clean_triplets[:int(total * 0.8)]
    valid_data = clean_triplets[int(total * 0.8):int(total * 0.9)]
    test_data  = clean_triplets[int(total * 0.9):]

    train_entities = set(s for s,p,o in train_data) | set(o for s,p,o in train_data)

    clean_valid, clean_test = [], []
    for triple in valid_data:
        s, p, o = triple
        if s in train_entities and o in train_entities:
            clean_valid.append(triple)
        else:
            train_data.append(triple)

    for triple in test_data:
        s, p, o = triple
        if s in train_entities and o in train_entities:
            clean_test.append(triple)
        else:
            train_data.append(triple)

    # Verify no leakage
    train_entities = set(s for s,p,o in train_data) | set(o for s,p,o in train_data)
    unseen_valid   = {s for s,p,o in clean_valid if s not in train_entities or o not in train_entities}
    unseen_test    = {s for s,p,o in clean_test  if s not in train_entities or o not in train_entities}

    print(f"Total  : {total:,}")
    print(f"Train  : {len(train_data):,}")
    print(f"Valid  : {len(clean_valid):,}")
    print(f"Test   : {len(clean_test):,}")
    print(f"Entités dans valid absentes du train : {len(unseen_valid)}")
    print(f"Entités dans test absentes du train  : {len(unseen_test)}")

    return train_data, clean_valid, clean_test


def save_split(data: list, filename: str):
    """Save a list of (s, p, o) triples to a tab-separated file."""
    with open(filename, "w", encoding="utf-8") as f:
        for s, p, o in data:
            f.write(f"{s}\t{p}\t{o}\n")


def save_all_splits(train_data, clean_valid, clean_test,
                    prefix: str = ""):
    """Save train/valid/test splits to .txt files."""
    save_split(train_data,  f"{prefix}train.txt")
    save_split(clean_valid, f"{prefix}valid.txt")
    save_split(clean_test,  f"{prefix}test.txt")
    print(f"Saved → {prefix}train.txt / valid.txt / test.txt")


def get_metrics(result) -> tuple:
    """Extract MRR, Hits@1, Hits@3, Hits@10 from a PyKEEN pipeline result."""
    return (
        result.metric_results.get_metric("mrr"),
        result.metric_results.get_metric("hits@1"),
        result.metric_results.get_metric("hits@3"),
        result.metric_results.get_metric("hits@10"),
    )


def print_metrics_table(results_dict: dict):
    """
    Print a comparison table of metrics for multiple models.
    results_dict: {model_name: (mrr, h1, h3, h10)}
    """
    models = list(results_dict.keys())
    header = f"{'Metric':<15}" + "".join(f"{m:>12}" for m in models)
    print("\n" + "=" * (15 + 12 * len(models)))
    print(header)
    print("-" * (15 + 12 * len(models)))
    for metric_name, idx in [("MRR", 0), ("Hits@1", 1), ("Hits@3", 2), ("Hits@10", 3)]:
        row = f"{metric_name:<15}"
        for m in models:
            row += f"{results_dict[m][idx]:>12.4f}"
        print(row)
    print("=" * (15 + 12 * len(models)))
